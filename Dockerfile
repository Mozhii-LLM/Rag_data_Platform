# =============================================================================
# Mozhii RAG Data Platform - Dockerfile
# =============================================================================
# Compatible with:
#   - HuggingFace Spaces (Docker SDK)  → port 7860, non-root uid 1000
#   - fly.io                           → set PORT=8080 in fly.toml env
#   - Render                           → set PORT=10000 via env
# =============================================================================

FROM python:3.11-slim

# ── System packages ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (required by HuggingFace Spaces) ───────────────────────────
# HF Spaces runs containers as uid=1000. Creating the user explicitly lets us
# set correct ownership on the data directory.
RUN useradd -m -u 1000 appuser

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==21.2.0

# ── Application source ────────────────────────────────────────────────────────
COPY . .

# ── Persistent data directories ───────────────────────────────────────────────
# Create full directory tree and give ownership to appuser.
RUN mkdir -p \
    data/pending/raw \
    data/pending/cleaned \
    data/pending/chunked/_locks \
    data/approved/raw \
    data/approved/cleaned \
    data/approved/chunked \
    && chown -R appuser:appuser /app

# ── Switch to non-root user ───────────────────────────────────────────────────
USER appuser

# ── Runtime configuration ─────────────────────────────────────────────────────
# HuggingFace Spaces requires port 7860.
# Override with PORT env var for fly.io (8080) or Render (10000).
ENV PORT=7860
EXPOSE 7860

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# ── Start command ─────────────────────────────────────────────────────────────
CMD ["gunicorn", "app:create_app()", "-c", "gunicorn_config.py"]
