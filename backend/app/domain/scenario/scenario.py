"""Scenario model and the single baseline scenario. Pure domain.

Language-neutral keys only (English); the UI localizes labels. Lever values are
clamped to their bounds before use, so out-of-range client input is safe.

Credits (kaizen budget): moving a lever away from its default costs credits —
improvement is an investment, not free. The budget is enforced at the game
boundary (``run_scenario``), NOT in ``build_config``: domain tests may probe
out-of-budget physics (e.g. the over-pacing thesis guards) directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from app.domain.scoring.score import ScoreWeights
from app.domain.simulation.line import LineConfig, StationSpec

# Lever keys — the contract shared with the HTTP API and the UI.
LEVER_BATCH_SIZE = "batch_size"
LEVER_RELEASE_INTERVAL = "release_interval"
LEVER_VARIANCE_FACTOR = "variance_factor"
LEVER_WIP_CAP = "wip_cap"


class KaizenBudgetExceededError(ValueError):
    """Requested lever moves cost more credits than the scenario's budget."""

    def __init__(self, cost: float, budget: float) -> None:
        self.cost = cost
        self.budget = budget
        super().__init__(f"kaizen budget exceeded: cost {cost} > budget {budget}")


class UnknownScenarioError(ValueError):
    """No scenario is registered under the requested id."""

    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"unknown scenario: {scenario_id}")


@dataclass(frozen=True)
class Lever:
    """A bounded, player-tunable input. Values are clamped to [minimum, maximum].

    ``cost_per_step`` prices each step moved away from ``default`` (staying at
    the default is free).
    """

    key: str
    minimum: float
    maximum: float
    step: float
    default: float
    cost_per_step: float

    def clamp(self, value: float) -> float:
        return max(self.minimum, min(self.maximum, value))

    def cost(self, value: float) -> float:
        """Credits required to move from the default to the (clamped) value."""
        return abs(self.clamp(value) - self.default) / self.step * self.cost_per_step


@dataclass(frozen=True)
class Scenario:
    """A fixed challenge. Server-owned line + three flow levers.

    ``ideal_lead_time`` is the theoretical one-piece-flow floor (sum of station
    cycle-time means) used to normalize the lead-time pillar of the score.

    The variance lever models STANDARD WORK investment: its value multiplies
    every station's cycle-time variance (1.0 = as-is, lower = steadier work).
    Means are untouched, so ``ideal_lead_time`` is unaffected.
    """

    scenario_id: str
    base_stations: tuple[StationSpec, ...]
    order_count: int
    delivery_window: float
    takt_time: float
    seed: int
    kaizen_budget: float
    batch_size_lever: Lever
    release_interval_lever: Lever
    variance_lever: Lever
    weights: ScoreWeights
    wip_cap_lever: Lever | None = None

    @property
    def ideal_lead_time(self) -> float:
        return sum(station.cycle_time_mean for station in self.base_stations)

    def levers(self) -> tuple[Lever, ...]:
        base = (self.batch_size_lever, self.release_interval_lever, self.variance_lever)
        if self.wip_cap_lever is not None:
            return (*base, self.wip_cap_lever)
        return base

    def applied_values(self, lever_values: Mapping[str, float]) -> dict[str, float]:
        """The lever values that would actually run, keyed by lever key.

        Missing keys fall back to the lever default; everything is clamped and
        whole-unit levers (batch, wip cap) are rounded. Cost and config are
        both derived from THIS, so the price always matches what runs.
        """
        applied: dict[str, float] = {}
        for lever in self.levers():
            value = lever.clamp(lever_values.get(lever.key, lever.default))
            if lever.key in (LEVER_BATCH_SIZE, LEVER_WIP_CAP):
                value = float(int(round(value)))
            applied[lever.key] = value
        return applied

    def credit_cost(self, lever_values: Mapping[str, float]) -> float:
        """Credits the requested lever values cost, priced on APPLIED values."""
        applied = self.applied_values(lever_values)
        return sum(lever.cost(applied[lever.key]) for lever in self.levers())

    def validate_budget(self, lever_values: Mapping[str, float]) -> float:
        """Return the credit cost, raising ``KaizenBudgetExceededError`` if over budget."""
        cost = self.credit_cost(lever_values)
        if cost > self.kaizen_budget + 1e-9:
            raise KaizenBudgetExceededError(cost, self.kaizen_budget)
        return cost

    def build_config(self, lever_values: Mapping[str, float]) -> LineConfig:
        """Apply (clamped) lever values to produce the effective line config.

        The seed and line layout come from the scenario, never the client. The
        variance factor scales every station's cycle-time variance (standard
        work). Does NOT enforce the budget (see module docstring) — that is a
        game rule applied by the RunScenario use case.
        """
        applied = self.applied_values(lever_values)
        factor = applied[LEVER_VARIANCE_FACTOR]
        stations = tuple(
            replace(station, cycle_time_variance=station.cycle_time_variance * factor)
            for station in self.base_stations
        )
        return LineConfig(
            stations=stations,
            order_count=self.order_count,
            delivery_window=self.delivery_window,
            takt_time=self.takt_time,
            seed=self.seed,
            batch_size=int(applied[LEVER_BATCH_SIZE]),
            release_interval=applied[LEVER_RELEASE_INTERVAL],
            wip_cap=(int(applied[LEVER_WIP_CAP]) if self.wip_cap_lever is not None else None),
        )


def baseline_scenario() -> Scenario:
    """The single baseline scenario: a three-station line (cut → weld → paint)
    whose bottleneck is weld. Lever defaults start deliberately sub-optimal (a
    batch of five, flooded release) so that improving flow visibly raises the
    score.

    Budget = 22 = exactly the cost of the full fix (batch 5→1 = 4, release
    0→6 = 12, variance 1.0→0.25 = 6): reaching the best flow takes the WHOLE
    budget spent on the right things — measured: full fix ≈ 89; standard work
    cannot rescue big batches (batch 5 + release 6 + variance 0.25, 18 credits
    ≈ 0 points). Over-pacing (release 12 = 24 credits) stays priced out.
    """
    return Scenario(
        scenario_id="baseline",
        base_stations=(
            StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=1.0),
            StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=2.0),
            StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=1.5),
        ),
        order_count=60,
        delivery_window=35.0,
        takt_time=6.0,
        seed=7,
        kaizen_budget=22.0,
        batch_size_lever=Lever(
            key=LEVER_BATCH_SIZE, minimum=1, maximum=20, step=1, default=5, cost_per_step=1.0
        ),
        release_interval_lever=Lever(
            key=LEVER_RELEASE_INTERVAL,
            minimum=0.0,
            maximum=12.0,
            step=0.5,
            default=0.0,
            cost_per_step=1.0,
        ),
        variance_lever=Lever(
            key=LEVER_VARIANCE_FACTOR,
            minimum=0.25,
            maximum=1.0,
            step=0.25,
            default=1.0,
            cost_per_step=2.0,
        ),
        # Flow-quality weights (sum to 1); delivery reliability gates the score.
        weights=ScoreWeights(lead_time=0.57, flow_efficiency=0.43),
    )


def unstable_line_scenario() -> Scenario:
    """The second scenario: structurally lean, wildly unsteady.

    The line already runs one-piece at takt (defaults batch 1, release = takt
    7.5 — the bottleneck keeps ~20% capacity headroom), but every station has
    CV≈1 cycle times (variance = mean²). The queues here are VARIABILITY-driven
    (Kingman), so the only fix that pays is standard work — the opposite ROI
    order of the baseline. Diagnose before you prescribe.

    Budget = 6 = exactly the standard-work full fix. Measured (seed 42):
    defaults ≈ 45 → variance 0.25 ≈ 81; misallocations are WORSE than doing
    nothing (batch fiddling ≈ 30, releasing faster than takt ≈ 38).
    """
    return Scenario(
        scenario_id="unstable_line",
        base_stations=(
            StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=16.0),
            StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=36.0),
            StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=25.0),
        ),
        order_count=60,
        delivery_window=35.0,
        takt_time=7.5,
        seed=42,
        kaizen_budget=6.0,
        batch_size_lever=Lever(
            key=LEVER_BATCH_SIZE, minimum=1, maximum=20, step=1, default=1, cost_per_step=1.0
        ),
        release_interval_lever=Lever(
            key=LEVER_RELEASE_INTERVAL,
            minimum=0.0,
            maximum=12.0,
            step=0.5,
            default=7.5,
            cost_per_step=1.0,
        ),
        variance_lever=Lever(
            key=LEVER_VARIANCE_FACTOR,
            minimum=0.25,
            maximum=1.0,
            step=0.25,
            default=1.0,
            cost_per_step=2.0,
        ),
        weights=ScoreWeights(lead_time=0.57, flow_efficiency=0.43),
    )


def pull_line_scenario() -> Scenario:
    """The third scenario: the pull challenge (CONWIP) in a chaotic plant.

    Same CV≈1 environment as the unstable line, but the WIP cap is a lever and
    RESCHEDULING IS FREE (release moves cost 0 — a schedule is planning, not
    investment). Defaults run careful takt-paced push, which drowns in the
    noise (≈27). Two honest strategies fit the budget of 8:

      * PULL: flood the eligibility (free) + tighten the cap — backlog at the
        door, few orders inside (classic CONWIP). Measured: cap 3 ≈ 74 for
        4.5 credits; the cap tunes like a real system (2 starves ≈ 38,
        4 too loose ≈ 58).
      * ROOT CAUSE: standard work at takt pacing ≈ 79 for 6 credits — slightly
        better, pricier, and it ONLY works with pacing kept (with flood and no
        cap it collapses to ≈ 20).

    Structure fiddling stays punished (batch 2 pull ≈ 11).
    """
    return Scenario(
        scenario_id="pull_line",
        base_stations=(
            StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=16.0),
            StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=36.0),
            StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=25.0),
        ),
        order_count=60,
        delivery_window=35.0,
        takt_time=7.5,
        seed=7,
        kaizen_budget=8.0,
        batch_size_lever=Lever(
            key=LEVER_BATCH_SIZE, minimum=1, maximum=20, step=1, default=1, cost_per_step=1.0
        ),
        release_interval_lever=Lever(
            key=LEVER_RELEASE_INTERVAL,
            minimum=0.0,
            maximum=12.0,
            step=0.5,
            default=7.5,
            cost_per_step=0.0,  # rescheduling is free — the point of the lesson
        ),
        variance_lever=Lever(
            key=LEVER_VARIANCE_FACTOR,
            minimum=0.25,
            maximum=1.0,
            step=0.25,
            default=1.0,
            cost_per_step=2.0,
        ),
        weights=ScoreWeights(lead_time=0.57, flow_efficiency=0.43),
        wip_cap_lever=Lever(
            key=LEVER_WIP_CAP, minimum=2, maximum=12, step=1, default=12, cost_per_step=0.5
        ),
    )


def scenarios() -> tuple[Scenario, ...]:
    """All playable scenarios, in presentation order."""
    return (baseline_scenario(), unstable_line_scenario(), pull_line_scenario())


def get_scenario(scenario_id: str) -> Scenario:
    """Look a scenario up by id, raising ``UnknownScenarioError`` if absent."""
    for scenario in scenarios():
        if scenario.scenario_id == scenario_id:
            return scenario
    raise UnknownScenarioError(scenario_id)
