"""Scenario model and the single baseline scenario. Pure domain.

Language-neutral keys only (English); the UI localizes labels. Lever values are
clamped to their bounds before use, so out-of-range client input is safe.

Credits (kaizen budget): moving a lever away from its default costs credits —
improvement is an investment, not free. The budget is enforced at the game
boundary (``run_scenario``), NOT in ``build_config``: domain tests may probe
out-of-budget physics (e.g. the over-pacing thesis guards) directly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.scoring.score import ScoreWeights
from app.domain.simulation.line import LineConfig, StationSpec

# Lever keys — the contract shared with the HTTP API and the UI.
LEVER_BATCH_SIZE = "batch_size"
LEVER_RELEASE_INTERVAL = "release_interval"
LEVER_VARIANCE_FACTOR = "variance_factor"


class KaizenBudgetExceededError(ValueError):
    """Requested lever moves cost more credits than the scenario's budget."""

    def __init__(self, cost: float, budget: float) -> None:
        self.cost = cost
        self.budget = budget
        super().__init__(f"kaizen budget exceeded: cost {cost} > budget {budget}")


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

    @property
    def ideal_lead_time(self) -> float:
        return sum(station.cycle_time_mean for station in self.base_stations)

    def levers(self) -> tuple[Lever, ...]:
        return (self.batch_size_lever, self.release_interval_lever, self.variance_lever)

    def applied_batch_size(self, batch_size: float) -> int:
        """The batch size the engine would actually use (clamped, whole units)."""
        return int(round(self.batch_size_lever.clamp(batch_size)))

    def applied_release_interval(self, release_interval: float) -> float:
        return self.release_interval_lever.clamp(release_interval)

    def applied_variance_factor(self, variance_factor: float) -> float:
        return self.variance_lever.clamp(variance_factor)

    def credit_cost(
        self,
        batch_size: float,
        release_interval: float,
        variance_factor: float = 1.0,
    ) -> float:
        """Credits the requested lever values cost, priced on APPLIED values —
        the cost always matches what ``build_config`` would actually run.
        """
        return (
            self.batch_size_lever.cost(self.applied_batch_size(batch_size))
            + self.release_interval_lever.cost(self.applied_release_interval(release_interval))
            + self.variance_lever.cost(self.applied_variance_factor(variance_factor))
        )

    def validate_budget(
        self,
        batch_size: float,
        release_interval: float,
        variance_factor: float = 1.0,
    ) -> float:
        """Return the credit cost, raising ``KaizenBudgetExceededError`` if over budget."""
        cost = self.credit_cost(batch_size, release_interval, variance_factor)
        if cost > self.kaizen_budget + 1e-9:
            raise KaizenBudgetExceededError(cost, self.kaizen_budget)
        return cost

    def build_config(
        self,
        batch_size: float,
        release_interval: float,
        variance_factor: float = 1.0,
    ) -> LineConfig:
        """Apply (clamped) lever values to produce the effective line config.

        The seed and line layout come from the scenario, never the client. The
        variance factor scales every station's cycle-time variance (standard
        work). Does NOT enforce the budget (see module docstring) — that is a
        game rule applied by the RunScenario use case.
        """
        factor = self.applied_variance_factor(variance_factor)
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
            batch_size=self.applied_batch_size(batch_size),
            release_interval=self.applied_release_interval(release_interval),
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
