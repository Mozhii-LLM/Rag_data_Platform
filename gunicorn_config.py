"""Gunicorn production server configuration."""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# ── Worker model ───────────────────────────────────────────────────────────────
# Use gthread (threaded sync) workers so multiple users can submit chunks /
# trigger pushes concurrently without blocking each other.
# Each worker spawns `threads` green-threads which share the process and the
# file-lock logic in chunking.py.
worker_class = 'gthread'
workers = 2       # 2 processes × threads = total concurrent capacity
threads = 4       # 4 threads per worker  → 8 simultaneous requests

# ── Timeouts ──────────────────────────────────────────────────────────────────
# The push-to-HuggingFace endpoint can take up to a few minutes when pushing
# large batch sets.  300 s gives ample headroom.
timeout = 300
graceful_timeout = 60
keepalive = 5
