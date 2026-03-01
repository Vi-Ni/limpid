# Limpid — Project Guide

## What is Limpid?
Educational investment dashboard for Canadian beginners. Shows what you hold, what it costs, and what you need to learn — without ever giving financial advice.

## Tech Stack
- **Backend**: Django 5.x, Python 3.12
- **Frontend**: Tailwind CSS v4 (via Vite), HTMX, Alpine.js
- **Build**: Vite (django-vite integration), uv for Python deps
- **DB**: SQLite (dev), PostgreSQL (prod)
- **i18n**: Django i18n, bilingual EN/FR
- **Hosting**: Raspberry Pi 4 via Cloudflare Tunnel at https://limpid.viniqo.com

## Project Structure
```
config/                  # Django project config
  settings/              # base.py, development.py, production.py, test.py
  urls.py                # Root URL conf
  context_processors.py  # nav_current (active nav state)
apps/
  accounts/              # User profiles, onboarding, risk quiz
  portfolio/             # Portfolio management
  real_estate/           # Real estate patrimony management
  market_data/           # Market data integration
  transparency/          # Fee/risk transparency reports
  education/             # Learning path & lessons
  scenarios/             # What-if scenario lab
  impact/                # Impact/ESG directory
templates/
  base.html              # Main layout (sidebar + bottom nav + main)
  components/            # Design system partials (see below)
  pages/                 # Full pages (home, styleguide, errors)
  account/               # Allauth overrides (login, signup, logout)
frontend/
  src/styles/main.css    # Tailwind v4 theme (@theme block)
  src/main.js            # Vite entry point
deploy/
  compose.prod.yml       # Production stack: PostgreSQL + App + Cloudflare Tunnel
scripts/
  setup-rpi.sh           # One-time RPi provisioning
  deploy.sh              # Redeploy latest image on RPi
locale/fr/LC_MESSAGES/   # French translations
instructions/            # Design docs & implementation plans
.claude/plans/           # Claude Code plan files
```

## Deployment

### Architecture
```
User → Cloudflare (HTTPS) → Tunnel → cloudflared → web:8000
                                         ↕
                                     db (PostgreSQL)
```

### Production stack (`deploy/compose.prod.yml`)
Three Docker containers on RPi (`vini@pich.local`):
- **db**: PostgreSQL 16-alpine
- **web**: `ghcr.io/vi-ni/limpid:latest` (Gunicorn, port 8000)
- **tunnel**: cloudflared (Cloudflare Tunnel to `limpid.viniqo.com`)

### CI/CD (`.github/workflows/ci.yml`)
On push to main: lint → test → build ARM64 image → push to GHCR.
Deployment is manual via SSH to RPi.

### Deploy a new version
```bash
ssh rpi "/opt/limpid/deploy.sh"
```

### RPi remote management
The agent has SSH access to the RPi via Cloudflare Tunnel (`ssh rpi`). This uses `cloudflared access ssh` as ProxyCommand (configured in `~/.ssh/config`), secured by Cloudflare Access (email OTP). Works regardless of network or WARP.

Common operations:
```bash
# Full deploy (pull image, recreate, migrate)
ssh rpi "/opt/limpid/deploy.sh"

# Check running containers
ssh rpi "cd /opt/limpid && docker compose -f compose.prod.yml ps"

# View logs (last 100 lines, all services)
ssh rpi "cd /opt/limpid && docker compose -f compose.prod.yml logs --tail=100"

# View logs for a specific service (web, db, tunnel)
ssh rpi "cd /opt/limpid && docker compose -f compose.prod.yml logs --tail=50 web"

# Restart a service
ssh rpi "cd /opt/limpid && docker compose -f compose.prod.yml restart web"

# Run Django management commands
ssh rpi "cd /opt/limpid && docker compose -f compose.prod.yml exec web python manage.py migrate --noinput"
ssh rpi "cd /opt/limpid && docker compose -f compose.prod.yml exec web python manage.py shell -c 'from django.contrib.auth.models import User; print(User.objects.count())'"

# Pull latest image without full deploy
ssh rpi "docker pull ghcr.io/vi-ni/limpid:latest"

# Check disk space
ssh rpi "df -h"

# Prune old Docker images
ssh rpi "docker image prune -f"
```

### RPi environment
- Host: `rpi` (SSH alias → `ssh.viniqo.com` via Cloudflare Tunnel → Raspberry Pi 4)
- Config: `/opt/limpid/.env` (SECRET_KEY, DATABASE_URL, TUNNEL_TOKEN, etc.)
- Compose: `/opt/limpid/compose.prod.yml`
- Deploy script: `/opt/limpid/deploy.sh`

### Containerfile notes
- Multi-stage: Node (frontend build) → Python (app)
- Templates + apps are copied into the frontend stage so Tailwind v4 `@source` directives can scan them
- `collectstatic` uses a dummy SECRET_KEY at build time
- WhiteNoise serves static files with `CompressedStaticFilesStorage` (not Manifest variant — Vite already handles cache busting)

## Design System ("Clair & calme")
- **Direction**: Off-white background, indigo primary, calm & trustworthy
- **Reference**: `instructions/Limpid_Design_Proposals.md`
- **Implementation**: `instructions/Design_System_Implementation_Plan.md`

### Theme tokens (defined in `frontend/src/styles/main.css`)
- `primary-{50..900}`: Indigo accent
- `bg-base` (#f8fafc), `bg-card` (#ffffff)
- `text` (#1e293b), `text-muted` (#64748b)
- `border` (#e2e8f0)
- `success-*`, `warning-*`, `danger-*`: Semantic colors

### Reusable components (`templates/components/`)
- `card_start.html` / `card_end.html` — Card wrapper (props: title, variant, icon)
- `badge.html` — Inline label (props: label, variant)
- `callout_start.html` / `callout_end.html` — Lesson callout (props: type, title)
- `metric_row.html` — Key-value row (props: label, value, annotation)
- `tooltip.html` — Educational popover, bottom-sheet on mobile (props: id, text)
- `progress_bar.html` — Step indicator (props: current, total)

Components use start/end pattern for slotted content:
```django
{% include "components/card_start.html" with title="My Card" %}
  <p>Any content here</p>
{% include "components/card_end.html" %}
```

### Navigation
- Desktop: Fixed sidebar (w-60) with icon + label nav items
- Mobile: Fixed bottom nav bar (5 items)
- Active state: `nav_current` context processor (from URL path)
- Styleguide: `/styleguide/` (DEBUG only)

## Commands
- **Dev server**: `uv run python manage.py runserver`
- **Vite**: `npm run dev` (from `frontend/`)
- **Tests**: `uv run pytest`
- **Lint**: `uv run ruff check . && uv run ruff format --check .`
- **Format**: `uv run ruff format .`
- **Translations**: `uv run python manage.py compilemessages`

## Conventions
- Code and comments in English
- All user-facing strings wrapped in `{% trans %}` or `gettext_lazy`
- French translations in `locale/fr/LC_MESSAGES/django.po`
- Tailwind classes use design system tokens (primary-600, text-muted, border, bg-base, etc.) — never raw blue-600/gray-* for themed elements
- Forms use `TAILWIND_SELECT_CLASS` from `apps/accounts/forms.py` for consistent styling

## Completed Milestones
- **M1**: Accounts & onboarding (user profiles, 3-step onboarding wizard, 6-question risk quiz)
- **Design System**: Tailwind theme, sidebar/bottom nav, reusable components, restyled all pages
- **Deployment**: RPi + Cloudflare Tunnel, CI/CD building ARM64 images to GHCR
- **Real Estate**: Full patrimony management — 9 models, co-ownership with evolving splits, Canadian mortgage amortization (semi-annual compounding), sale simulation with GST/QST/capital gains, HTMX expense/valuation tracking, 54 tests, full FR translations

## URL Patterns
| Prefix | App |
|--------|-----|
| `/` | Home |
| `/accounts/` | Auth (allauth) + profiles/onboarding |
| `/portfolio/` | Portfolio management |
| `/learn/` | Education/learning path |
| `/scenarios/` | Scenario lab |
| `/impact/` | Impact directory |
| `/transparency/` | Transparency reports |
| `/market/` | Market data |
| `/real-estate/` | Real estate patrimony management |
| `/styleguide/` | Design system reference (DEBUG only) |

## Gotchas & Lessons Learned
- **Containerfile — Tailwind scanning**: Templates and `apps/` must be copied into the frontend build stage so Tailwind v4 `@source` directives can scan HTML classes. Without this, Tailwind purges all utility classes used in templates.
- **Containerfile — collectstatic**: `collectstatic` needs `SECRET_KEY=build-only` env var at build time since production settings require it.
- **WhiteNoise storage**: Use `CompressedStaticFilesStorage`, NOT `CompressedManifestStaticFilesStorage` — Vite already hashes filenames, double-hashing breaks the manifest lookup.
- **GHCR image name**: `github.repository` may contain uppercase (`Vi-Ni/limpid`), must lowercase it for Docker tags — use `${IMAGE_NAME,,}` in CI.
- **ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS**: Must match the exact domain in Cloudflare (`viniqo.com`, not `viniko.com`).
- **Docker Compose v2**: Use `docker compose` (no hyphen) on modern Docker — the old `docker-compose` pip package is deprecated.
- **RPi SSH**: Use `ssh rpi` (Cloudflare Tunnel via `ssh.viniqo.com`), not `ssh vini@pich.local` — WARP blocks local network from IDE terminals. The tunnel is secured by Cloudflare Access (email OTP). `host.docker.internal` doesn't work on Linux RPi; the tunnel target is `ssh://172.17.0.1:22` (Docker bridge IP).
- **Django FK named `property`**: Never name a ForeignKey field `property` — it shadows Python's `@property` decorator, causing `TypeError: 'ForeignKey' object is not callable` on any model property. The `Mortgage` model uses `real_estate` as the FK name instead.
