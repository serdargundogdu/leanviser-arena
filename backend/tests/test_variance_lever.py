"""Standard-work (variance) lever: steadier work means better flow — but it
cannot rescue structurally bad flow (big batches). Variability is the waste
this lever removes; the queueing physics reward it only on a sound base.
"""

import pytest

from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import baseline_scenario


def _run(batch_size: float, release_interval: float, variance_factor: float):
    return run_scenario(
        RunScenarioCommand(
            scenario=baseline_scenario(),
            lever_values={
                "batch_size": batch_size,
                "release_interval": release_interval,
                "variance_factor": variance_factor,
            },
        )
    )


def test_build_config_scales_station_variances_not_means() -> None:
    scenario = baseline_scenario()
    config = scenario.build_config(
        {"batch_size": 1, "release_interval": 6.0, "variance_factor": 0.5}
    )
    for station, base in zip(config.stations, scenario.base_stations, strict=True):
        assert station.cycle_time_variance == pytest.approx(base.cycle_time_variance * 0.5)
        assert station.cycle_time_mean == base.cycle_time_mean
    # Ideal lead time (sum of means) is therefore unchanged.
    assert scenario.ideal_lead_time == 15.0


def test_variance_factor_is_clamped() -> None:
    scenario = baseline_scenario()
    low = scenario.applied_values({"variance_factor": 0.1})["variance_factor"]
    high = scenario.applied_values({"variance_factor": 2.0})["variance_factor"]
    assert low == scenario.variance_lever.minimum
    assert high == scenario.variance_lever.maximum


def test_standard_work_improves_takt_paced_flow() -> None:
    takt = baseline_scenario().takt_time
    as_is = _run(1, takt, 1.0)
    standardized = _run(1, takt, 0.25)
    assert standardized.score.composite > as_is.score.composite
    assert standardized.metrics.flow_efficiency > as_is.metrics.flow_efficiency
    assert standardized.metrics.lead_time_median < as_is.metrics.lead_time_median


def test_standard_work_cannot_rescue_big_batches() -> None:
    # Spending on variance while leaving the batch at 5 (18 credits, in budget)
    # must not beat the plain two-lever fix — flow structure comes first.
    takt = baseline_scenario().takt_time
    misallocated = _run(5, takt, 0.25)
    two_lever_fix = _run(1, takt, 1.0)
    assert misallocated.score.composite < two_lever_fix.score.composite
