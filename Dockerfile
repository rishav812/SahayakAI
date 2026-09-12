# syntax=docker/dockerfile:1
#
# This file is the RECIPE for building your app's container ("the box").
# Two stages keep the final image small and clean:
#   - builder stage: installs dependencies (needs extra tools)
#   - runtime stage: only the app + installed deps, nothing else
# This "build vs runtime separation" is exactly the Q2 interview point.

##############################
# Stage 1 — builder
##############################
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Isolated virtual environment we can copy to the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy ONLY requirements first so this layer caches unless requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


##############################
# Stage 2 — runtime (the image that actually ships)
##############################
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# SECURITY: never run as root in production.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Bring over the ready-made virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy your application source, owned by the non-root user.
COPY --chown=appuser:appuser . .

# Chroma's persistent client creates CHROMA_DIR itself if it's missing, but /app
# is root-owned (WORKDIR ran before USER below) and chroma_db/ is now excluded
# from the build context via .dockerignore — pre-create it and hand it to
# appuser so a fresh container can still write to it.
RUN mkdir -p /app/chroma_db && chown -R appuser:appuser /app/chroma_db

USER appuser

EXPOSE 8000

# HEALTHCHECK — needs a GET /health route in your FastAPI app (Phase 0 step).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"

# Start the server. app.main:app matches your package layout (run from repo root).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]