"""Discrete-event simulation (DES) of a station-generic production line.

Modules:
  * ``line``    — pure model: Station, Order, ProductionLine config (value objects).
  * ``engine``  — deterministic, seeded discrete-event simulation → EventLog.
  * ``metrics`` — flow metrics derived from an EventLog (lead time, WIP,
                  flow efficiency, throughput, delivery reliability).

Determinism contract: same ``LineConfig`` (seed included) → bit-identical
result. All randomness comes from a single seeded RNG in ``engine``.
"""
