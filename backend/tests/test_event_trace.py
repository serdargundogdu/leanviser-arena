"""Station-level event trace invariants — the replay data must be physically
consistent: chronological per order, exclusive per station server, and anchored
to the system-level release/completion timestamps.
"""

from collections import defaultdict

import pytest

from app.domain.scenario.scenario import baseline_scenario, pull_line_scenario
from app.domain.simulation.engine import simulate

CONFIGS = {
    "baseline_flood_batch5": baseline_scenario().build_config({}),
    "baseline_lean": baseline_scenario().build_config({"batch_size": 1, "release_interval": 6.0}),
    "pull_conwip": pull_line_scenario().build_config({"release_interval": 0.0, "wip_cap": 3}),
}


@pytest.mark.parametrize("label", CONFIGS)
def test_trace_covers_every_order_and_station(label: str) -> None:
    config = CONFIGS[label]
    log = simulate(config)
    assert len(log.visits) == config.order_count * config.station_count


@pytest.mark.parametrize("label", CONFIGS)
def test_trace_is_chronological_per_order(label: str) -> None:
    config = CONFIGS[label]
    log = simulate(config)
    by_order: dict[int, list] = defaultdict(list)
    for visit in log.visits:
        by_order[visit.order_id].append(visit)
    for order in log.orders:
        visits = sorted(by_order[order.order_id], key=lambda v: v.station_index)
        # Anchors: the trace starts at release; processing ends no later than
        # completion (with batch > 1 the order waits in the outbound batch
        # buffer between its last finish and the batch flush = completion).
        assert visits[0].queued_at == pytest.approx(order.release_time)
        assert visits[-1].finished_at <= order.completion_time + 1e-9
        previous_finish = None
        for visit in visits:
            assert visit.queued_at <= visit.started_at <= visit.finished_at
            if previous_finish is not None:
                # Batch waiting may delay the hand-off, never reverse it.
                assert previous_finish <= visit.queued_at
            previous_finish = visit.finished_at


def test_one_piece_flow_completes_at_the_last_finish() -> None:
    # With batch = 1 there is no outbound batch wait: completion == last finish.
    log = simulate(CONFIGS["baseline_lean"])
    last_finish = {
        visit.order_id: visit.finished_at for visit in log.visits if visit.station_index == 2
    }
    for order in log.orders:
        assert last_finish[order.order_id] == pytest.approx(order.completion_time)


@pytest.mark.parametrize("label", CONFIGS)
def test_station_processes_one_order_at_a_time(label: str) -> None:
    config = CONFIGS[label]
    log = simulate(config)
    by_station: dict[int, list] = defaultdict(list)
    for visit in log.visits:
        by_station[visit.station_index].append(visit)
    for visits in by_station.values():
        visits.sort(key=lambda v: v.started_at)
        for earlier, later in zip(visits, visits[1:], strict=False):
            assert earlier.finished_at <= later.started_at + 1e-9
