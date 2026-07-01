"""Scenario domain — a playable challenge wrapping a base production line.

A Scenario pins the immutable parts of a run (line layout, order volume,
delivery window, RNG seed) on the server and exposes a small set of bounded
LEVERS the player may tune. The client sends only lever values, never the seed,
so runs stay server-authoritative and reproducible. v0.2 ships exactly one
baseline scenario with two flow levers.
"""
