# syntax=docker/dockerfile:1.7

# ─── Base ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    HARVESTHERO_DEV_DIR=/data \
    HARVESTHERO_COOKIE_SECURE=1

# Copy the WHOLE repo — we need database.py, auth.py, paths.py from
# the root plus the web/ subdirectory itself.
WORKDIR /app
COPY . /app

# Install just the web app's deps.
RUN pip install -r /app/web/requirements.txt

# /data is where Fly.io mounts the persistent volume. paths.py picks
# this up via HARVESTHERO_DEV_DIR and puts the sqlite file at
# /data/data/inventory.db.
VOLUME ["/data"]

EXPOSE 8080

# Run gunicorn from web/ so relative template/static paths resolve.
WORKDIR /app/web
CMD ["gunicorn", "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
