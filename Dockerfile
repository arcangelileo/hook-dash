# =============================================================================
# HookDash — Production Dockerfile
# Multi-stage build with non-root user, health check, and proper signal handling
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build dependencies
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a prefix we can copy later
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install . uvicorn[standard]

# ---------------------------------------------------------------------------
# Stage 2: Production image
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the installed packages from builder — no gcc/dev headers in final image
COPY --from=builder /install /usr/local

# Create non-root user and data directory
RUN groupadd --gid 1000 hookdash && \
    useradd --uid 1000 --gid hookdash --shell /bin/bash --create-home hookdash && \
    mkdir -p /app/data && \
    chown -R hookdash:hookdash /app

# Copy application code
COPY --chown=hookdash:hookdash alembic.ini ./
COPY --chown=hookdash:hookdash alembic/ ./alembic/
COPY --chown=hookdash:hookdash src/ ./src/

# Default configuration — override via environment variables
ENV HOOKDASH_DATABASE_URL="sqlite+aiosqlite:///./data/hookdash.db" \
    HOOKDASH_SECRET_KEY="change-me-in-production"

# Switch to non-root user
USER hookdash

EXPOSE 8000

# Health check — hit /health every 30 s, fail after 3 s, start checking after 10 s
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

# Use exec form so uvicorn receives SIGTERM directly (proper signal handling)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
