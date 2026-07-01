"""Domain invariants — the physics of flow the engine must always obey, and the
reward thesis it must protect.

Covered:
  * flowEfficiency lies in (0, 1].
  * Little's Law identity: time-average WIP == throughput * mean lead time
    (exact here because the system starts and ends empty).
  * Smaller transfer batches lower the median lead time (one-piece flow wins).
  * Overproduction (flooding releases) inflates WIP and depresses flow
    efficiency WITHOUT buying extra throughput — throughput is never rewarded.
"""

import pytest

from app.domain.simulation.engine import simulate
from app.domain.simulation.line import LineConfig, StationSpec
from app.domain.simulation.metrics import compute_metrics

STATIONS = (
    StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=1.0),
    StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=2.0),  # bottleneck
    StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=1.5),
)
DUE_DATE = 800.0


def _config(**overrides: object) -> LineConfig:
    params: dict = dict(
        stations=STATIONS,
        order_count=60,
        due_date=DUE_DATE,
        seed=7,
    )
    params.update(overrides)
    return LineConfig(**params)


def test_flow_efficiency_in_unit_interval() -> None:
    metrics = compute_metrics(simulate(_config()), due_date=DUE_DATE)
    assert 0.0 < metrics.flow_efficiency <= 1.0


def test_littles_law_identity() -> None:
    config = _config()
    log = simulate(config)
    metrics = compute_metrics(log, due_date=DUE_DATE)

    # System starts and ends empty ⇒ area under the WIP curve == Σ lead time.
    area_under_wip = metrics.average_wip * metrics.makespan
    total_lead_time = sum(order.lead_time for order in log.orders)
    assert area_under_wip == pytest.approx(total_lead_time, rel=1e-9)

    # Therefore L == λ · W (avg WIP == throughput · mean lead time).
    assert metrics.average_wip == pytest.approx(
        metrics.throughput * metrics.lead_time_mean, rel=1e-9
    )


def test_smaller_batch_lowers_median_lead_time() -> None:
    # Identical config and seed; only the transfer batch differs.
    large_batch = compute_metrics(simulate(_config(batch_size=10)), due_date=DUE_DATE)
    one_piece = compute_metrics(simulate(_config(batch_size=1)), due_date=DUE_DATE)
    assert one_piece.lead_time_median < large_batch.lead_time_median


def test_overproduction_inflates_wip_without_higher_throughput() -> None:
    # Flood: release everything at t=0 (classic overproduction / push).
    flood = compute_metrics(simulate(_config(release_interval=0.0)), due_date=DUE_DATE)
    # Levelled: release in step with the bottleneck cadence (~weld cycle time).
    levelled = compute_metrics(simulate(_config(release_interval=6.0)), due_date=DUE_DATE)

    # Overproduction inflates work-in-process ...
    assert flood.average_wip > levelled.average_wip
    # ... and depresses flow efficiency (more waiting per value-added minute) ...
    assert flood.flow_efficiency < levelled.flow_efficiency
    # ... yet buys NO extra throughput: the line is bottleneck-limited.
    assert flood.throughput <= levelled.throughput * 1.05
