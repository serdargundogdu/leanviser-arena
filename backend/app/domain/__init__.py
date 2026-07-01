"""Domain layer — pure business rules, framework-free.

No FastAPI, no DB, no I/O. Invariants live with the model (no anemic types).
The simulation subpackage holds the deterministic discrete-event engine that is
the authority for all flow metrics; nothing here depends on outer layers.
"""
