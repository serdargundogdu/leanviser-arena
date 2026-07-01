"""Application layer — use cases orchestrating the domain.

Thin coordination only: no business rules (those live in ``domain``) and no
framework/transport concerns (those live in ``adapters``). Holds the
``RunSimulation`` use case that composes engine + metrics.
"""
