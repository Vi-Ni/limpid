# Deploy Limpid to RPi at limpid.viniko.com

## Context
Deploy the Limpid Django app to a Raspberry Pi (`vini@pich.local`) served at `https://limpid.viniko.com` using **Cloudflare Tunnel** — no port forwarding, no certificate management, works with dynamic IPs. The CI already builds ARM64 images to GHCR.

**Architecture:**
```
User → Cloudflare (HTTPS) → Tunnel → cloudflared → web:8000
                                         ↕
                                     db (PostgreSQL)
```

---

## Files to create/modify in the repo

### 1. Create `deploy/compose.prod.yml`
Production Podman Compose stack with 3 services:

```yaml
services:
  db:
    image: docker.io/library/postgres:16-alpine
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U limpid"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    image: ghcr.io/vi-ni/limpid:latest
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    expose:
      - "8000"

  tunnel:
    image: docker.io/cloudflare/cloudflared:latest
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN}
    depends_on:
      - web
    restart: unless-stopped

volumes:
  pgdata:
```

No Caddy needed — Cloudflare handles TLS and HTTPS.

### 2. Create `scripts/setup-rpi.sh`
One-time RPi provisioning script:
1. Install Podman + podman-compose via apt
2. Prompt for GHCR login (GitHub PAT)
3. Create `/opt/limpid/` directory
4. Copy `compose.prod.yml`
5. Generate `.env` with random `SECRET_KEY` and `POSTGRES_PASSWORD`, prompt for `TUNNEL_TOKEN`
6. Pull images, start stack
7. Run migrations + seed commands
8. Prompt for superuser creation

### 3. Rewrite `scripts/deploy.sh`
Switch from raw `podman run` to `podman-compose`:
- Pull latest app image
- `podman-compose up -d --force-recreate web` (only recreate app, not db/tunnel)
- Run migrations
- Show status

### 4. Modify `.env.example`
Add `POSTGRES_*` and `TUNNEL_TOKEN` variables, update `DATABASE_URL` host to `db`, update example domain to `limpid.viniko.com`.

### 5. Fix git remote URL
Update origin from `Vi-Ni/limpide.git` to `Vi-Ni/limpid.git`.

### 6. No changes to Django settings or CI/CD
- `config/settings/production.py` already has `SECURE_PROXY_SSL_HEADER` for `X-Forwarded-Proto` (Cloudflare sets this)
- No auto-deploy job — deployment stays manual

---

## Manual steps: Cloudflare Tunnel setup (step-by-step)

### Step 1 — Create the tunnel on Cloudflare
1. Go to https://one.dash.cloudflare.com (Cloudflare Zero Trust dashboard)
2. In the left sidebar: **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as connector
5. Name it: `limpid`
6. Click **Save tunnel**
7. **Copy the tunnel token** (long string starting with `eyJ...`) — you'll need it for `.env`

### Step 2 — Configure the public hostname
Still in the tunnel setup page:
1. Go to the **Public Hostname** tab
2. Click **Add a public hostname**
3. Fill in:
   - **Subdomain**: `limpid`
   - **Domain**: `viniko.com`
   - **Type**: `HTTP`
   - **URL**: `web:8000`
4. Click **Save hostname**

Cloudflare automatically creates the DNS record (CNAME) for `limpid.viniko.com` pointing to the tunnel.

### Step 3 — First deployment on RPi
```bash
# From local machine: copy files to RPi
scp scripts/setup-rpi.sh deploy/compose.prod.yml vini@pich.local:~/

# SSH into RPi and run setup
ssh vini@pich.local
chmod +x ~/setup-rpi.sh
~/setup-rpi.sh
# → It will ask for the tunnel token from Step 1
```

### Subsequent deployments
```bash
ssh vini@pich.local
/opt/limpid/deploy.sh
```

---

## Verification
1. `podman-compose -f compose.prod.yml ps` — all 3 services (db, web, tunnel) Up
2. Cloudflare dashboard: tunnel shows **Healthy** status
3. `https://limpid.viniko.com` in browser — app loads with valid HTTPS
4. Check static assets load (CSS/JS) in browser DevTools
