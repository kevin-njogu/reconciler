# =============================================================================
# Stage 1: Build the React frontend
# =============================================================================
FROM node:20-alpine AS frontend-build

WORKDIR /build

# Install dependencies first (layer-cached until package files change)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY frontend/ .
RUN npm run build


# =============================================================================
# Stage 2: Combined runtime image (FastAPI + nginx)
#
# nginx  (port 8080) — serves the React SPA and proxies /api/ to gunicorn
# gunicorn (port 8000) — runs the FastAPI application internally
# supervisord — manages both processes in the single container
# =============================================================================
FROM python:3.11-slim

# Install nginx and supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Africa/Nairobi
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ---------------------------------------------------------------------------
# Python backend
# ---------------------------------------------------------------------------
WORKDIR /app/backend

# Install Python dependencies (layer-cached until requirements change)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/alembic.ini .
COPY backend/alembic/ alembic/
COPY backend/app/ app/

# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------
COPY --from=frontend-build /build/dist /usr/share/nginx/html

# ---------------------------------------------------------------------------
# nginx configuration
# ---------------------------------------------------------------------------
# Remove the default site so only our config is active
RUN rm -f /etc/nginx/sites-enabled/default

COPY nginx.conf /etc/nginx/conf.d/default.conf

# ---------------------------------------------------------------------------
# supervisord configuration
# ---------------------------------------------------------------------------
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ---------------------------------------------------------------------------
# Non-root user for the backend process
# Nginx master process must stay as root to bind port 8080;
# worker processes drop privileges automatically.
# ---------------------------------------------------------------------------
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app/backend

# Cloud Run expects port 8080
ENV PORT=8080
EXPOSE 8080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
