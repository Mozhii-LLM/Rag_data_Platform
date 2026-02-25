# =============================================================================
# Mozhii RAG Data Platform - Dockerfile
# =============================================================================
# Builds a production-ready container image for fly.io deployment.
#
# Multi-stage is overkill here; a single slim stage keeps things simple
# while still being lean (~200 MB final image).
# =============================================================================

FROM python:3.11-slim

# ── System packages ───────────────────────────────────────────────────────────
# No extra system deps required for this Flask + HuggingFace app.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first so Docker can cache this layer independently
# from source code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==21.2.0

# ── Application source ────────────────────────────────────────────────────────
COPY . .

# ── Persistent data directories ───────────────────────────────────────────────
# Create the full directory tree so the app can start even before the
# fly.io volume is attached (volume replaces this at runtime).
RUN mkdir -p \
    data/pending/raw \
    data/pending/cleaned \
    data/pending/chunked/_locks \
    data/approved/raw \
    data/approved/cleaned \
    data/approved/chunked

# ── Runtime configuration ─────────────────────────────────────────────────────
# fly.io routes external HTTPS → internal 8080.
# Gunicorn reads PORT from the environment (set in fly.toml).
ENV PORT=8080
EXPOSE 8080

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# ── Start command ─────────────────────────────────────────────────────────────
CMD ["gunicorn", "app:create_app()", "-c", "gunicorn_config.py"]
