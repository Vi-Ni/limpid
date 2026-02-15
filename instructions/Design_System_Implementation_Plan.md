# Design System & Layout Implementation Plan

## Context
M1 (accounts & onboarding) is complete. The app works functionally but uses raw Tailwind utilities with no design system, default blue-600 palette, and a simple topbar navigation. The design proposals doc (`Limpide_Design_Proposals.md`) defines direction **A "Clair & calme"** — off-white bg, blue-gray/indigo accent, sidebar nav on desktop, bottom nav on mobile, and a library of reusable components. This plan implements that design foundation before starting M2.

## Scope
- Tailwind v4 theme (CSS custom properties for "Clair & calme" palette)
- Navigation restructure: sidebar desktop + bottom nav mobile
- Reusable component partials (card, badge, callout, metric row, tooltip, progress bar)
- Restyle all existing pages (home, auth, profile, onboarding, quiz)
- Styleguide page (dev-only)
- French translations for new strings

**Out of scope**: new features/pages, 5-step onboarding (M2+), dark mode, search bar, chart integrations.

## Steps (all completed)

### 1. Tailwind theme — "Clair & calme" palette ✅
**Commit**: `ed37f4b`

**File**: `frontend/src/styles/main.css`

Added `@theme` block with:
- Primary: indigo-600 family (`--color-primary-*`)
- Background: `--color-bg-base: #f8fafc`, `--color-bg-card: #ffffff`
- Text: `--color-text: #1e293b`, `--color-text-muted: #64748b`
- Border: `--color-border: #e2e8f0`
- Semantic: success (green), warning (amber), danger (red)
- Base layer: body 15px/1.6 typography
- `@utility container-limpide` (max-width 1200px)

### 2. Navigation — sidebar + bottom nav ✅
**Commit**: `4693e6a`

- `templates/base.html` — Desktop: `<aside>` sidebar (w-60, fixed left) + `<main>` with `md:pl-60` offset. Mobile: content full-width, bottom nav fixed.
- `templates/components/nav.html` — Sidebar with SVG icons, nav items (Home, Portfolios, Learn, Scenarios, Impact), profile/auth section at bottom. Active state via `nav_current` context variable.
- `templates/components/bottom_nav.html` — Fixed bottom bar (`md:hidden`), 5 items with SVG icons + labels.
- `templates/components/footer.html` — Added `pb-20 md:pb-0` for bottom nav spacing.
- `config/context_processors.py` — `nav_current()` determines active section from URL path.
- `config/settings/base.py` — Registered context processor.

### 3. Reusable component templates ✅
**Commit**: `7da5f80`

Created in `templates/components/`:

| File | Usage | Props (via `{% include with %}`) |
|------|-------|------|
| `card_start.html` / `card_end.html` | Wrapper card with slotted content | `variant` (default/warning/success), `title`, `icon` |
| `badge.html` | Inline labels | `label`, `variant` (info/success/warning/danger/neutral) |
| `callout_start.html` / `callout_end.html` | Lesson callouts with slotted content | `type` (info/warning/example/impact), `title` |
| `metric_row.html` | Key-value display | `label`, `value`, `annotation` |
| `tooltip.html` | Educational popover (bottom-sheet on mobile) | `id`, `text` — Alpine.js toggle |
| `progress_bar.html` | Step indicator | `current`, `total` |

### 4. Restyle home page ✅
**Commit**: `3dd830a`

**File**: `templates/pages/home.html`

- Hero: "Understand before you invest" + subtitle + CTA
- 3 pillars: Transparency, Education, No advice — using card component with SVG icons
- "How it works" section: 3 numbered steps (profile → explore → understand)
- All colors migrated from `blue-600` → `primary-600`

### 5. Restyle auth & accounts pages ✅
**Commit**: `5427d3b`

Files modified (blue→indigo, card component, design system tokens):
- `templates/account/login.html`
- `templates/account/signup.html`
- `templates/account/logout.html`
- `apps/accounts/templates/accounts/profile.html`
- `apps/accounts/templates/accounts/onboarding.html` + 3 step partials
- `apps/accounts/templates/accounts/risk_quiz.html` + quiz partials
- `apps/accounts/forms.py` — `TAILWIND_SELECT_CLASS` updated

### 6. Styleguide page (dev-only) ✅
**Commit**: `032c085`

- `templates/pages/styleguide.html` — Showcases: colors, typography, buttons, cards, badges, callouts, metric rows, tooltips, progress bars, form elements
- `apps/accounts/urls_home.py` — Added `/styleguide/` route
- `apps/accounts/views.py` — Added `styleguide_view` (404 if not DEBUG)

### 7. i18n — French translations ✅
**Commit**: `d8e1b40`

`locale/fr/LC_MESSAGES/django.po` — Added translations for:
- Nav labels: Home/Accueil, Main navigation, Mobile navigation
- Home page copy: "Understand before you invest", "How it works", step descriptions
- Component text: "Got it"/"Compris", "Step X of Y"
- Styleguide: "Design System Styleguide"

## Verification
- `uv run ruff check . && uv run ruff format --check .` → all passed
- `uv run pytest` → 32/32 tests pass
- Visual: check at 375px (mobile), 768px (tablet), 1280px (desktop)
- Sidebar collapses on mobile, bottom nav shows
- HTMX flows: onboarding + quiz still work after restyle
- `/styleguide/` page renders all components
