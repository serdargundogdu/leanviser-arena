"""Release-gate semantics: the WIP cap COMPOSES with paced release.

An order becomes eligible on its release schedule and enters only when the cap
allows; blocked orders wait outside the system (their lead time starts at
actual entry). No cap must be bit-identical to the pre-gate push engine.
"""

from app.domain.simulation.engine import simulate
from app.domain.simulation.line import LineConfig, StationSpec

STATIONS = (
    StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=1.0),
    StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=2.0),
    StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=1.5),
)


def _config(**overrides: object) -> LineConfig:
    params: dict = dict(
        stations=STATIONS,
        order_count=60,
        delivery_window=35.0,
        takt_time=6.0,
        seed=7,
        batch_size=1,
        release_interval=0.0,
    )
    params.update(overrides)
    return LineConfig(**params)


def _max_wip(log) -> int:
    return max(level for _, level in log.wip_samples)


def test_loose_cap_is_bit_identical_to_no_cap() -> None:
    # A cap that never binds (>= order_count) must not change anything.
    uncapped = simulate(_config(wip_cap=None))
    loose = simulate(_config(wip_cap=60))
    assert [o.lead_time for o in uncapped.orders] == [o.lead_time for o in loose.orders]
    assert uncapped.wip_samples == loose.wip_samples


def test_wip_never_exceeds_the_cap() -> None:
    log = simulate(_config(wip_cap=4))
    assert _max_wip(log) <= 4


def test_cap_bounds_lead_time_under_flood() -> None:
    # Flooded release: uncapped WIP piles up and inflates lead time; a tight
    # cap keeps orders outside until there is room, so in-system time stays low.
    flood = simulate(_config(wip_cap=None))
    pulled = simulate(_config(wip_cap=3))
    flood_mean = sum(o.lead_time for o in flood.orders) / len(flood.orders)
    pulled_mean = sum(o.lead_time for o in pulled.orders) / len(pulled.orders)
    assert pulled_mean < flood_mean / 3


def test_cap_composes_with_pacing_instead_of_overriding_it() -> None:
    # With a cap, pacing still schedules ELIGIBILITY: releases can be later
    # than the pull would allow, never earlier. Under a loose-enough cap and
    # slow pacing, entries follow the schedule exactly.
    paced = simulate(_config(wip_cap=10, release_interval=6.0))
    release_times = sorted(o.release_time for o in paced.orders)
    scheduled = [k * 6.0 for k in range(60)]
    assert all(
        actual >= expected for actual, expected in zip(release_times, scheduled, strict=True)
    )


def test_pull_is_robust_to_the_release_schedule() -> None:
    # The pull lesson: with a tight cap, flood vs takt pacing barely matters —
    # the cap self-regulates the line. Compare mean lead times.
    flood_pull = simulate(_config(wip_cap=3, release_interval=0.0))
    paced_pull = simulate(_config(wip_cap=3, release_interval=6.0))
    flood_mean = sum(o.lead_time for o in flood_pull.orders) / 60
    paced_mean = sum(o.lead_time for o in paced_pull.orders) / 60
    assert abs(flood_mean - paced_mean) < 0.35 * max(flood_mean, paced_mean)
