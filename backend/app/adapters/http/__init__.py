"""HTTP driving adapter — FastAPI router and transport DTOs.

Thin translation layer: DTOs in/out, use case in the middle, no business logic.
Depends inward on ``application`` and ``domain``; nothing depends back on it.
"""
