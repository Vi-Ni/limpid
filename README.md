# Limpide

Educational investment dashboard for beginners (Quebec/Canada first). Radical transparency: see exactly what you hold, what it costs, what it risks, and how to learn — without ever receiving personalized investment advice.

## Tech Stack

- **Backend**: Django 5.2, django-allauth, django-htmx
- **Frontend**: Django templates + HTMX + Alpine.js + Tailwind CSS v4
- **Bundler**: Vite (Chart.js + TradingView Lightweight Charts)
- **Database**: PostgreSQL 16
- **Package manager**: uv
- **Container**: Podman/Docker (multi-stage build, arm64)
- **CI/CD**: GitHub Actions → GHCR → Raspberry Pi + Cloudflare Tunnel

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- PostgreSQL 16 (or use SQLite for quick local dev)
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start PostgreSQL (via Podman)
podman run -d --name limpide-db \
  -e POSTGRES_DB=limpide \
  -e POSTGRES_USER=limpide \
  -e POSTGRES_PASSWORD=limpide \
  -p 5432:5432 \
  postgres:16-alpine

# Or use SQLite (create .env at project root)
echo "DATABASE_URL=sqlite:///db.sqlite3" > .env

# Run migrations
uv run python manage.py migrate

# Start dev servers (2 terminals)
cd frontend && npm run dev        # Terminal 1: Vite (port 5173)
uv run python manage.py runserver # Terminal 2: Django (port 8000)
```

Open **http://localhost:8000**.

### Using Docker Compose

```bash
podman-compose up  # or docker compose up
```

## Development

```bash
# Lint
uv run ruff check .
uv run ruff format --check .

# Test
uv run pytest

# Pre-commit hooks
uv run pre-commit install
```

## Project Structure

```
limpide/
├── apps/                 # Django apps
│   ├── accounts/         # Auth, profile, onboarding, risk quiz
│   ├── portfolio/        # Sandbox & imported portfolios, CSV import
│   ├── market_data/      # Securities, ETF holdings, price history
│   ├── transparency/     # Fee calc, look-through, risk metrics
│   ├── education/        # Learning path, glossary, contextual tips
│   ├── scenarios/        # "What if" simulator
│   └── impact/           # Local/alternative investment directory
├── config/               # Django project config (split settings)
├── frontend/             # Vite + Tailwind + HTMX + Alpine
├── templates/            # Project-level templates
├── locale/               # i18n (fr + en)
├── scripts/              # Deployment & seed helpers
├── Containerfile         # Multi-stage container build
└── compose.yml           # Local dev with PostgreSQL
```

## Milestones

- [x] **M0** — Project scaffold
- [ ] **M1** — Accounts & onboarding
- [ ] **M2** — Market data & portfolio basics
- [ ] **M3** — Portfolio visualization & CSV import
- [ ] **M4** — Transparency dashboard
- [ ] **M5** — Education crescendo
- [ ] **M6** — Scenario lab
- [ ] **M7** — Impact explorer
- [ ] **M8** — Polish (i18n, a11y, mobile)

## License

Private — All rights reserved.
