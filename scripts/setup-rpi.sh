#!/usr/bin/env bash
# One-time Raspberry Pi setup for Limpid deployment
# Usage: clone the repo on the RPi, then run this script.
set -euo pipefail

DEPLOY_DIR="/opt/limpid"

echo "==> Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "    Docker installed. You may need to log out and back in for group changes."
fi

echo ""
echo "==> Logging in to GitHub Container Registry..."
echo "    Create a Personal Access Token at https://github.com/settings/tokens"
echo "    with 'read:packages' scope."
read -rp "GitHub username: " GH_USER
read -rsp "GitHub PAT: " GH_PAT
echo ""
echo "$GH_PAT" | docker login ghcr.io -u "$GH_USER" --password-stdin

echo ""
echo "==> Creating deployment directory at ${DEPLOY_DIR}..."
sudo mkdir -p "$DEPLOY_DIR"
sudo chown "$(whoami):$(whoami)" "$DEPLOY_DIR"

echo "==> Copying deployment files..."
cp ~/compose.prod.yml "$DEPLOY_DIR/compose.prod.yml"

echo ""
echo "==> Generating environment file..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    SECRET=$(openssl rand -base64 50 | tr -d '\n')
    DB_PASS=$(openssl rand -base64 24 | tr -d '\n')

    echo "    You need the Cloudflare Tunnel token."
    echo "    Find it at: https://one.dash.cloudflare.com → Networks → Tunnels → limpid"
    read -rp "Tunnel token: " TUNNEL_TOKEN

    cat > "$DEPLOY_DIR/.env" <<EOF
# Django
SECRET_KEY=${SECRET}
DJANGO_SETTINGS_MODULE=config.settings.production

# Database (host 'db' = compose service name)
DATABASE_URL=postgres://limpid:${DB_PASS}@db:5432/limpid

# Production
ALLOWED_HOSTS=limpid.viniko.com,localhost
CSRF_TRUSTED_ORIGINS=https://limpid.viniko.com

# PostgreSQL container
POSTGRES_DB=limpid
POSTGRES_USER=limpid
POSTGRES_PASSWORD=${DB_PASS}

# Cloudflare Tunnel
TUNNEL_TOKEN=${TUNNEL_TOKEN}
EOF
    echo "    .env created with generated secrets."
else
    echo "    .env already exists, skipping."
fi

echo ""
echo "==> Starting all services..."
cd "$DEPLOY_DIR"
docker compose -f compose.prod.yml up -d

echo "==> Waiting for database to be ready..."
sleep 10

echo "==> Running migrations..."
docker compose -f compose.prod.yml exec web python manage.py migrate --noinput

echo ""
echo "==> Creating superuser..."
docker compose -f compose.prod.yml exec web python manage.py createsuperuser

echo ""
echo "==> Seeding initial data..."
docker compose -f compose.prod.yml exec web python manage.py seed_securities || true
docker compose -f compose.prod.yml exec web python manage.py seed_education || true
docker compose -f compose.prod.yml exec web python manage.py seed_impact || true

echo ""
echo "==> Setup complete!"
echo "    Visit https://limpid.viniko.com to verify."
echo ""
docker compose -f compose.prod.yml ps
