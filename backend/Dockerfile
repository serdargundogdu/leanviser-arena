# Multi-stage build for the LeanViser ARENA backend.
# Stage 1 resolves dependencies into a virtualenv with uv; stage 2 is a slim
# runtime that only carries the venv + app code. Cloud Run injects $PORT.

# ---- builder ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (cached layer) using only the lockfiles.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Then copy the application source.
COPY app ./app

# ---- runtime ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Bring over the resolved venv and the app code from the builder.
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# Cloud Run sets $PORT; default to 8080 for local runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
