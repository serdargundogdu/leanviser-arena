"""LeanViser ARENA backend.

Modular monolith with a hexagonal (ports & adapters) layout. Dependencies flow
inward only:

    adapters/  →  application/  →  domain/

``domain`` is framework-free and knows nothing about HTTP or persistence.
``shared`` holds cross-cutting primitives with no layer dependencies.
"""
