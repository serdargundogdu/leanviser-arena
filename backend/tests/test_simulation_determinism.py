"""Determinism contract: same config (seed) → bit-identical results.

This is a fairness + copy-protection guarantee — a run must be reproducible on
the server from its seed alone, with no dependence on wall-clock or platform.
"""

from app.domain.simulation.engine import simulate
from app.domain.simulation.line import LineConfig, StationSpec
from app.domain.simulation.metrics import compute_metrics

STATIONS = (
    StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=1.0),
    StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=2.0),
    StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=1.5),
)


def _config(seed: int = 42, batch_size: int = 1) -> LineConfig:
    return LineConfig(
        stations=STATIONS,
        order_count=40,
        delivery_window=60.0,
        takt_time=6.0,
        seed=seed,
        batch_size=batch_size,
    )


def test_same_seed_bit_identical_event_log() -> None:
    log1 = simulate(_config())
    log2 = simulate(_config())
    assert [o.lead_time for o in log1.orders] == [o.lead_time for o in log2.orders]
    assert [o.value_added_time for o in log1.orders] == [o.value_added_time for o in log2.orders]
    assert log1.wip_samples == log2.wip_samples


def test_same_seed_same_metrics() -> None:
    metrics1 = compute_metrics(simulate(_config()), takt_time=6.0, delivery_window=60.0)
    metrics2 = compute_metrics(simulate(_config()), takt_time=6.0, delivery_window=60.0)
    assert metrics1 == metrics2


def test_different_seed_changes_result() -> None:
    metrics1 = compute_metrics(simulate(_config(seed=1)), takt_time=6.0, delivery_window=60.0)
    metrics2 = compute_metrics(simulate(_config(seed=2)), takt_time=6.0, delivery_window=60.0)
    # Distinct seeds drive distinct cycle-time draws → distinct flow metrics.
    assert metrics1 != metrics2
