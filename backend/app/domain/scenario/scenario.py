"""Scenario model and the single v0.2 baseline scenario. Pure domain.

Language-neutral keys only (English); the UI localizes labels. Lever values are
clamped to their bounds before use, so out-of-range client input is safe.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.scoring.score import ScoreWeights
from app.domain.simulation.line import LineConfig, StationSpec

# Lever keys — the contract shared with the HTTP API and the UI.
LEVER_BATCH_SIZE = "batch_size"
LEVER_RELEASE_INTERVAL = "release_interval"


@dataclass(frozen=True)
class Lever:
    """A bounded, player-tunable input. Values are clamped to [minimum, maximum]."""

    key: str
    minimum: float
    maximum: float
    step: float
    default: float

    def clamp(self, value: float) -> float:
        return max(self.minimum, min(self.maximum, value))


@dataclass(frozen=True)
class Scenario:
    """A fixed challenge. Server-owned line + two flow levers.

    ``ideal_lead_time`` is the theoretical one-piece-flow floor (sum of station
    cycle-time means) used to normalize the lead-time pillar of the score.
    """

    scenario_id: str
    base_stations: tuple[StationSpec, ...]
    order_count: int
    delivery_window: float
    takt_time: float
    seed: int
    batch_size_lever: Lever
    release_interval_lever: Lever
    weights: ScoreWeights

    @property
    def ideal_lead_time(self) -> float:
        return sum(station.cycle_time_mean for station in self.base_stations)

    def levers(self) -> tuple[Lever, ...]:
        return (self.batch_size_lever, self.release_interval_lever)

    def build_config(self, batch_size: float, release_interval: float) -> LineConfig:
        """Apply (clamped) lever values to produce the effective line config.

        The seed and line layout come from the scenario, never the client.
        """
        return LineConfig(
            stations=self.base_stations,
            order_count=self.order_count,
            delivery_window=self.delivery_window,
            takt_time=self.takt_time,
            seed=self.seed,
            batch_size=int(round(self.batch_size_lever.clamp(batch_size))),
            release_interval=self.release_interval_lever.clamp(release_interval),
        )


def baseline_scenario() -> Scenario:
    """The single v0.2 scenario: a three-station line (cut → weld → paint) whose
    bottleneck is weld. Lever defaults start deliberately sub-optimal (a batch of
    five, flooded release) so that improving flow visibly raises the score.
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
        batch_size_lever=Lever(key=LEVER_BATCH_SIZE, minimum=1, maximum=20, step=1, default=5),
        release_interval_lever=Lever(
            key=LEVER_RELEASE_INTERVAL, minimum=0.0, maximum=12.0, step=0.5, default=0.0
        ),
        # Flow-quality weights (sum to 1); delivery reliability gates the score.
        weights=ScoreWeights(lead_time=0.57, flow_efficiency=0.43),
    )
