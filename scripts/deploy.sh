#!/usr/bin/env bash
# RPi deployment helper
set -euo pipefail

IMAGE="ghcr.io/${GITHUB_USER:-user}/limpid:latest"
CONTAINER_NAME="limpid-web"
ENV_FILE="/opt/limpid/.env"

echo "Pulling latest image..."
podman pull "$IMAGE"

echo "Stopping existing container..."
podman stop "$CONTAINER_NAME" 2>/dev/null || true
podman rm "$CONTAINER_NAME" 2>/dev/null || true

echo "Starting new container..."
podman run -d \
  --name "$CONTAINER_NAME" \
  --env-file "$ENV_FILE" \
  -p 127.0.0.1:8000:8000 \
  --restart unless-stopped \
  "$IMAGE"

echo "Running migrations..."
podman exec "$CONTAINER_NAME" python manage.py migrate --noinput

echo "Deployment complete."
