"""Flow metrics derived from a simulation ``EventLog``. Pure functions.

The reward thesis lives here in spirit: we expose leadTime, flowEfficiency,
WIP, throughput and deliveryReliability — but NOT a composite score and NOT a
throughput-maximizing objective. Overproduction surfaces as inflated WIP and
depressed flow efficiency, never as a reward. (Composite scoring arrives in a
later slice; keeping it out here is deliberate.)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from app.domain.simulation.engine import EventLog


@dataclass(frozen=True)
class SimulationMetrics:
    """Flow metrics for a single run. All times are in the config's time units.

    ``flow_efficiency`` is value-added time over lead time and lies in (0, 1].
    ``throughput`` is orders per unit time over the makespan — reported, not
    rewarded. ``average_wip`` is the time-average work-in-process.
    """

    lead_time_median: float
    lead_time_mean: float
    average_wip: float
    flow_efficiency: float
    throughput: float
    delivery_reliability: float
    order_count: int
    makespan: float


def _average_wip(log: EventLog) -> float:
    """Time-average WIP = area under the WIP step function / makespan.

    Because the system starts and ends empty, this area equals the sum of all
    per-order lead times — the exact form of Little's Law used by the invariant
    tests (see ``tests/test_simulation_invariants.py``).
    """
    makespan = log.makespan
    if makespan <= 0:
        return 0.0
    area = 0.0
    samples = log.wip_samples
    for (t0, level), (t1, _next_level) in zip(samples, samples[1:], strict=False):
        area += level * (t1 - t0)
    return area / makespan


def compute_metrics(log: EventLog, delivery_window: float) -> SimulationMetrics:
    """Derive flow metrics from an event log and a promised delivery window."""
    lead_times = [order.lead_time for order in log.orders]
    total_lead_time = sum(lead_times)
    total_value_added = sum(order.value_added_time for order in log.orders)
    order_count = len(log.orders)
    makespan = log.makespan
    on_time = sum(1 for order in log.orders if order.is_on_time(delivery_window))

    return SimulationMetrics(
        lead_time_median=statistics.median(lead_times),
        lead_time_mean=statistics.fmean(lead_times),
        average_wip=_average_wip(log),
        flow_efficiency=total_value_added / total_lead_time,
        throughput=order_count / makespan,
        delivery_reliability=on_time / order_count,
        order_count=order_count,
        makespan=makespan,
    )
