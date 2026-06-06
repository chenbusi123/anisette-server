# Multi-stage Dockerfile for Anisette Provisioning Server
# Stage 1: Build
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install requirements
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    XDG_DATA_HOME="/data" \
    XDG_CONFIG_HOME="/config"

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Create storage directories
RUN mkdir -p /data /config

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start server
ENTRYPOINT ["python", "app.py"]
