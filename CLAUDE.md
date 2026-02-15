# Limpide — Project Guide

## What is Limpide?
Educational investment dashboard for Canadian beginners. Shows what you hold, what it costs, and what you need to learn — without ever giving financial advice.

## Tech Stack
- **Backend**: Django 5.x, Python 3.14
- **Frontend**: Tailwind CSS v4 (via Vite), HTMX, Alpine.js
- **Build**: Vite (django-vite integration), uv for Python deps
- **DB**: SQLite (dev), PostgreSQL (prod)
- **i18n**: Django i18n, bilingual EN/FR

## Project Structure
```
config/                  # Django project config
  settings/              # base.py, development.py, production.py, test.py
  urls.py                # Root URL conf
  context_processors.py  # nav_current (active nav state)
apps/
  accounts/              # User profiles, onboarding, risk quiz
  portfolio/             # Portfolio management
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
locale/fr/LC_MESSAGES/   # French translations
instructions/            # Design docs & implementation plans
```

## Design System ("Clair & calme")
- **Direction**: Off-white background, indigo primary, calm & trustworthy
- **Reference**: `instructions/Limpide_Design_Proposals.md`
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
- **Translations**: `uv run python manage.py compilemessages`
- **Format**: `uv run ruff format .`

## Conventions
- Code and comments in English
- All user-facing strings wrapped in `{% trans %}` or `gettext_lazy`
- French translations in `locale/fr/LC_MESSAGES/django.po`
- Tailwind classes use design system tokens (primary-600, text-muted, border, bg-base, etc.) — never raw blue-600/gray-* for themed elements
- Forms use `TAILWIND_SELECT_CLASS` from `apps/accounts/forms.py` for consistent styling

## Completed Milestones
- **M1**: Accounts & onboarding (user profiles, 3-step onboarding wizard, 6-question risk quiz)
- **Design System**: Tailwind theme, sidebar/bottom nav, reusable components, restyled all pages

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
| `/styleguide/` | Design system reference (DEBUG only) |
