"""Scenario + lever behavior: bounded, clamped, and server-authoritative config."""

from app.domain.scenario.scenario import (
    LEVER_BATCH_SIZE,
    LEVER_RELEASE_INTERVAL,
    baseline_scenario,
)


def test_baseline_exposes_two_levers() -> None:
    scenario = baseline_scenario()
    keys = {lever.key for lever in scenario.levers()}
    assert keys == {LEVER_BATCH_SIZE, LEVER_RELEASE_INTERVAL}


def test_ideal_lead_time_is_sum_of_cycle_means() -> None:
    # cut 4 + weld 6 + paint 5
    assert baseline_scenario().ideal_lead_time == 15.0


def test_lever_clamp() -> None:
    lever = baseline_scenario().batch_size_lever
    assert lever.clamp(lever.minimum - 10) == lever.minimum
    assert lever.clamp(lever.maximum + 10) == lever.maximum
    assert lever.clamp(3) == 3


def test_build_config_applies_lever_values() -> None:
    scenario = baseline_scenario()
    config = scenario.build_config(batch_size=3, release_interval=6.0)
    assert config.batch_size == 3
    assert config.release_interval == 6.0
    # Server-owned parts come from the scenario, not the client.
    assert config.seed == scenario.seed
    assert config.stations == scenario.base_stations
    assert config.delivery_window == scenario.delivery_window


def test_build_config_clamps_out_of_range_input() -> None:
    scenario = baseline_scenario()
    config = scenario.build_config(batch_size=1000, release_interval=-5.0)
    assert config.batch_size == int(scenario.batch_size_lever.maximum)
    assert config.release_interval == scenario.release_interval_lever.minimum


def test_batch_size_is_rounded_to_int() -> None:
    config = baseline_scenario().build_config(batch_size=3.7, release_interval=0.0)
    assert config.batch_size == 4
