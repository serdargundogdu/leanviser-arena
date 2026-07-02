"""Deterministic discrete-event simulation (DES) of a production line.

Pure and seedable: given the same ``LineConfig`` (seed included) it produces a
bit-identical ``EventLog``. All randomness comes from a single
``random.Random(seed)``; event ties break on a monotonic sequence counter, so
the processing order — and therefore the RNG draw order — is a total order.

Mechanics:
  * N stations in series, one server each (single-piece processing per station).
  * RELEASE GATE: order ``k`` becomes ELIGIBLE at ``k * release_interval``
    (0 = flood at t=0) and actually enters the line only when the optional
    ``wip_cap`` allows (WIP < cap). Blocked orders wait OUTSIDE the system in
    FIFO order; each departure admits the next one at that instant. The two
    controls therefore COMPOSE: no cap = pure paced push; cap + flood =
    classic CONWIP pull; cap + pacing = paced release with a WIP ceiling.
    An order's lead time starts at actual entry (release), not eligibility —
    the takt-based demand schedule still judges delivery by completion time,
    so holding orders outside cannot game the delivery gate.
  * TRANSFER BATCHING: a finished unit waits at its station until ``batch_size``
    units have accumulated, then the whole batch moves downstream at once. This
    is why larger batches inflate lead time: early finishers wait for batchmates.

The engine records an event log; ``metrics.py`` derives lead time, WIP, flow
efficiency, throughput and delivery reliability from it. No scoring here — the
reward thesis is a metrics/scoring concern, not an engine concern.
"""

from __future__ import annotations

import heapq
import itertools
import math
import random
from collections import deque
from dataclasses import dataclass

from app.domain.simulation.line import Distribution, LineConfig, Order

# Event kinds. Only used to dispatch; never participates in heap ordering
# (the unique sequence number guarantees a total order first).
_ARRIVAL = 0
_COMPLETE = 1


@dataclass(frozen=True)
class StationVisit:
    """One order's pass through one station: queue entry, processing window.

    The gap between ``finished_at`` here and ``queued_at`` at the next station
    is transfer-batch waiting (a full batch moves at the same instant).
    """

    order_id: int
    station_index: int
    queued_at: float
    started_at: float
    finished_at: float


@dataclass(frozen=True)
class EventLog:
    """Immutable record of a completed simulation run.

    ``orders`` carry release/completion timestamps and accumulated value-added
    time. ``wip_samples`` is a step function ``(time, level_after_change)`` of
    work-in-process, time-sorted, starting at ``(horizon_start, 0)`` and ending
    at ``(horizon_end, 0)`` — the system begins and ends empty. ``visits`` is
    the full station-level trace (order × station), sorted by (order, station),
    enough to replay the run visually.
    """

    orders: tuple[Order, ...]
    wip_samples: tuple[tuple[float, int], ...]
    visits: tuple[StationVisit, ...]
    horizon_start: float
    horizon_end: float

    @property
    def makespan(self) -> float:
        return self.horizon_end - self.horizon_start


def _lognormal_params(mean: float, variance: float) -> tuple[float, float]:
    """Convert desired mean/variance of a lognormal into the (mu, sigma) of its
    underlying normal, so config can be given in intuitive cycle-time terms.
    """
    if variance == 0.0:
        # Degenerate: sigma → 0, draws collapse to the mean.
        return math.log(mean), 0.0
    sigma_sq = math.log(1.0 + variance / (mean * mean))
    mu = math.log(mean) - sigma_sq / 2.0
    return mu, math.sqrt(sigma_sq)


def simulate(config: LineConfig) -> EventLog:
    """Run the DES and return its event log. Deterministic in ``config.seed``."""
    rng = random.Random(config.seed)
    n_stations = config.station_count
    orders = [Order(order_id=i) for i in range(config.order_count)]

    # Pre-compute (mu, sigma) per station once; sampling stays in event order.
    ln_params = [
        _lognormal_params(s.cycle_time_mean, s.cycle_time_variance) for s in config.stations
    ]

    # Event heap of (time, seq, kind, station_idx, order). ``seq`` is a unique
    # monotonic tiebreaker → total order → deterministic RNG draw sequence.
    heap: list[tuple[float, int, int, int, Order]] = []
    seq = itertools.count()

    def schedule(time: float, kind: int, station_idx: int, order: Order) -> None:
        heapq.heappush(heap, (time, next(seq), kind, station_idx, order))

    # Per-station state.
    queues: list[deque[Order]] = [deque() for _ in range(n_stations)]
    busy = [False] * n_stations
    batch_buffer: list[list[Order]] = [[] for _ in range(n_stations)]
    processed_at = [0] * n_stations  # units that finished processing at station i

    # WIP step function; starts empty at t=0.
    wip = 0
    wip_samples: list[tuple[float, int]] = [(0.0, 0)]

    # Station-level trace for replay: (order, station) → [queued, started, finished].
    visit_track: dict[tuple[int, int], list[float]] = {}

    def record_wip(time: float, delta: int) -> None:
        nonlocal wip
        wip += delta
        wip_samples.append((time, wip))

    # Release gate. Every order is scheduled at its ELIGIBILITY time; entry is
    # gated by the WIP cap in on_arrival. Blocked orders wait outside (FIFO)
    # and are admitted one-per-departure in flush_batch.
    blocked: deque[Order] = deque()
    for k, order in enumerate(orders):
        schedule(k * config.release_interval, _ARRIVAL, 0, order)

    def sample_cycle_time(station_idx: int) -> float:
        spec = config.stations[station_idx]
        if spec.distribution is not Distribution.LOGNORMAL:  # pragma: no cover
            raise NotImplementedError(f"unsupported distribution: {spec.distribution}")
        mu, sigma = ln_params[station_idx]
        if sigma == 0.0:
            return math.exp(mu)
        return rng.lognormvariate(mu, sigma)

    def start_processing(time: float, station_idx: int) -> None:
        order = queues[station_idx].popleft()
        busy[station_idx] = True
        visit_track[(order.order_id, station_idx)][1] = time
        cycle_time = sample_cycle_time(station_idx)
        if config.stations[station_idx].value_added:
            order.value_added_time += cycle_time
        schedule(time + cycle_time, _COMPLETE, station_idx, order)

    def flush_batch(time: float, station_idx: int) -> None:
        batch = batch_buffer[station_idx]
        batch_buffer[station_idx] = []
        if station_idx == n_stations - 1:
            for order in batch:
                order.completion_time = time
                record_wip(time, -1)
                # One out → the next blocked (eligible) order may come in.
                if blocked:
                    schedule(time, _ARRIVAL, 0, blocked.popleft())
        else:
            for order in batch:
                schedule(time, _ARRIVAL, station_idx + 1, order)

    def on_arrival(time: float, station_idx: int, order: Order) -> None:
        if station_idx == 0:
            # The gate: an eligible order enters only if the cap allows.
            if config.wip_cap is not None and wip >= config.wip_cap:
                blocked.append(order)
                return
            order.release_time = time
            record_wip(time, +1)
        visit_track[(order.order_id, station_idx)] = [time, -1.0, -1.0]
        queues[station_idx].append(order)
        if not busy[station_idx]:
            start_processing(time, station_idx)

    def on_complete(time: float, station_idx: int, order: Order) -> None:
        busy[station_idx] = False
        visit_track[(order.order_id, station_idx)][2] = time
        batch_buffer[station_idx].append(order)
        processed_at[station_idx] += 1
        # Flush when the transfer batch is full, or when this station has seen
        # every order (no scrap in push) — the latter flushes a final partial.
        if (
            len(batch_buffer[station_idx]) >= config.batch_size
            or processed_at[station_idx] == config.order_count
        ):
            flush_batch(time, station_idx)
        if queues[station_idx]:
            start_processing(time, station_idx)

    # Main dispatch loop.
    while heap:
        time, _s, kind, station_idx, order = heapq.heappop(heap)
        if kind == _ARRIVAL:
            on_arrival(time, station_idx, order)
        else:
            on_complete(time, station_idx, order)

    if any(o.completion_time is None for o in orders):  # pragma: no cover
        raise RuntimeError("simulation ended with unfinished orders (engine bug)")

    horizon_start = min(o.release_time for o in orders)  # type: ignore[type-var]
    horizon_end = max(o.completion_time for o in orders)  # type: ignore[type-var]
    visits = tuple(
        StationVisit(
            order_id=order_id,
            station_index=station_idx,
            queued_at=times[0],
            started_at=times[1],
            finished_at=times[2],
        )
        for (order_id, station_idx), times in sorted(visit_track.items())
    )
    return EventLog(
        orders=tuple(orders),
        wip_samples=tuple(wip_samples),
        visits=visits,
        horizon_start=horizon_start,
        horizon_end=horizon_end,
    )
