#!/usr/bin/env bash
# Deploy latest Limpid image to RPi
# Run this on the RPi: /opt/limpid/deploy.sh
set -euo pipefail

DEPLOY_DIR="/opt/limpid"
IMAGE="ghcr.io/vi-ni/limpid:latest"

cd "$DEPLOY_DIR"

echo "==> Pulling latest image..."
docker pull "$IMAGE"

echo "==> Restarting web service..."
docker-compose -f compose.prod.yml up -d --force-recreate web

echo "==> Waiting for web container..."
sleep 5

echo "==> Running migrations..."
docker-compose -f compose.prod.yml exec web python manage.py migrate --noinput

echo "==> Deployment complete."
docker-compose -f compose.prod.yml ps
