"""Pure domain model for a station-generic production line.

Framework-free: no FastAPI, no DB, no I/O. Everything here is deterministic
data plus invariants expressed in the Ubiquitous Language (Station, Order,
ProductionLine). The discrete-event engine (``engine.py``) consumes these
structures; metrics (``metrics.py``) are computed from the event log it emits.

The model is STATION-GENERIC by design: N stations in series, each with its own
stochastic cycle time. A single line is just the special case used in v0.1;
pull / line-balancing challenges extend the same structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ReleasePolicy(StrEnum):
    """How orders enter the line. v0.1 ships PUSH only."""

    PUSH = "push"


class Distribution(StrEnum):
    """Cycle-time sampling family. v0.1 ships LOGNORMAL only."""

    LOGNORMAL = "lognormal"


@dataclass(frozen=True)
class StationSpec:
    """Immutable configuration of one station.

    ``cycle_time_mean`` / ``cycle_time_variance`` describe the cycle time in
    intuitive terms (time units); the engine converts them to the underlying
    distribution parameters. ``value_added`` marks processing here as
    value-adding for flow-efficiency accounting (all stations are VA in v0.1).
    """

    name: str
    cycle_time_mean: float
    cycle_time_variance: float
    distribution: Distribution = Distribution.LOGNORMAL
    value_added: bool = True

    def __post_init__(self) -> None:
        if self.cycle_time_mean <= 0:
            raise ValueError("cycle_time_mean must be > 0")
        if self.cycle_time_variance < 0:
            raise ValueError("cycle_time_variance must be >= 0")


@dataclass(frozen=True)
class LineConfig:
    """Full, self-contained simulation input (seedable → reproducible).

    ``stations`` is ordered upstream→downstream. ``order_count`` orders are
    released per ``release_policy``; ``release_interval`` paces PUSH releases
    (0.0 = flood: everything at t=0). Delivery is judged against a takt-paced
    DEMAND schedule: order ``k`` is due at ``k * takt_time + delivery_window``
    (``takt_time`` = customer demand cadence, ``delivery_window`` = allowed lead
    time). Releasing slower than takt cannot keep up with demand.
    ``batch_size`` is the transfer batch (units accumulated at a station before
    moving downstream together). ``wip_cap`` optionally caps orders in process
    (CONWIP-like); None = no cap.
    """

    stations: tuple[StationSpec, ...]
    order_count: int
    delivery_window: float
    takt_time: float
    seed: int
    batch_size: int = 1
    release_policy: ReleasePolicy = ReleasePolicy.PUSH
    release_interval: float = 0.0
    wip_cap: int | None = None

    def __post_init__(self) -> None:
        if not self.stations:
            raise ValueError("at least one station is required")
        if self.order_count <= 0:
            raise ValueError("order_count must be > 0")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if self.release_interval < 0:
            raise ValueError("release_interval must be >= 0")
        if self.delivery_window <= 0:
            raise ValueError("delivery_window must be > 0")
        if self.takt_time <= 0:
            raise ValueError("takt_time must be > 0")
        if self.wip_cap is not None and self.wip_cap <= 0:
            raise ValueError("wip_cap must be > 0 when set")

    @property
    def station_count(self) -> int:
        return len(self.stations)


@dataclass
class Order:
    """A single unit flowing through the line.

    Mutable: the engine stamps timestamps as the order progresses.
    ``value_added_time`` accumulates the processing durations actually incurred
    (the numerator of flowEfficiency). Time-in-system (``lead_time``) is release
    → completion.
    """

    order_id: int
    release_time: float | None = None
    completion_time: float | None = None
    value_added_time: float = field(default=0.0)

    @property
    def lead_time(self) -> float:
        if self.release_time is None or self.completion_time is None:
            raise ValueError(f"order {self.order_id} not yet completed")
        return self.completion_time - self.release_time

    def is_on_time(self, takt_time: float, delivery_window: float) -> bool:
        """On time when finished by this order's takt-paced demand due date.

        Order ``k``'s demand due date is ``k * takt_time + delivery_window`` —
        fixed by the customer's cadence, independent of when it was released. So
        releasing slower than takt (starving the line) misses the schedule.
        """
        if self.completion_time is None:
            raise ValueError(f"order {self.order_id} not yet completed")
        due_date = self.order_id * takt_time + delivery_window
        return self.completion_time <= due_date
