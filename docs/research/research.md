# Limpid — Deep Codebase Research Report

## 1. Product Vision & Mission

**Limpid** is an educational investment dashboard for Canadian (Quebec-first) beginners, now expanded to support French users. Core promise:

> "See exactly what you hold, what it costs, what it risks, and how to learn — without ever receiving personalized investment advice."

The product is deliberately **non-prescriptive**: no CTAs like "Buy now", no financial advice, no opinion. It empowers users through education, transparency, and scenario exploration.

**Target user**: Quebec/Canada and France beginner investors who want to understand their portfolio and real estate patrimony without being sold to or overwhelmed by jargon.

**Key philosophy**: "Comprendre avant d'investir" (Understand before you invest).

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.2, Python 3.12 |
| Auth | django-allauth (email-based login) |
| Frontend | Tailwind CSS v4 (via Vite), HTMX 2, Alpine.js 3 |
| Typography | Geist Sans + Geist Mono (CDN) |
| Charts | Chart.js 4 (doughnut, bar, line with custom plugins), lightweight-charts 4 (TradingView-style line) |
| Build | Vite 6 + @tailwindcss/vite, uv for Python deps |
| DB | PostgreSQL 16 (dev + prod), in-memory SQLite (test only) |
| i18n | Django i18n, bilingual EN/FR, French default |
| Static files | WhiteNoise (CompressedStaticFilesStorage) |
| Hosting | Raspberry Pi 4 via Cloudflare Tunnel |
| CI/CD | GitHub Actions → GHCR (ARM64 images) |
| Linting | Ruff (check + format), pre-commit hooks |
| Testing | pytest + pytest-django + pytest-cov |

---

## 3. Project Structure

```
limpid/
├── apps/
│   ├── accounts/              # Auth, profiles, onboarding, risk quiz
│   ├── portfolio/             # Portfolio management, holdings, transactions
│   ├── market_data/           # Asset catalog, seed data
│   ├── real_estate/           # Real estate patrimony management (most complex)
│   │   ├── models.py          # 15 models (~435 lines)
│   │   ├── views.py           # 30 view functions (~1155 lines)
│   │   ├── services.py        # Financial math engine (~684 lines)
│   │   ├── forms.py           # 10 form classes (~454 lines)
│   │   ├── urls.py            # 34 URL patterns
│   │   ├── admin.py           # All models registered with inlines
│   │   ├── signals.py         # user_logged_in signal for pending invitations
│   │   ├── tooltips.py        # Country-aware educational tooltip system (~179 lines)
│   │   ├── exchange_rates.py  # Currency conversion API + cache + fallback
│   │   ├── templatetags/      # real_estate_filters.py (6 filters/tags)
│   │   ├── tests/             # test_models, test_services, test_views, test_filters
│   │   └── migrations/        # 0001-0008 (8 migrations)
│   ├── transparency/          # Fee/risk transparency (NOT IMPLEMENTED)
│   ├── education/             # Learning path, lessons, quizzes
│   ├── scenarios/             # What-if simulator (SCAFFOLDED)
│   └── impact/                # ESG/impact directory (SCAFFOLDED)
├── config/
│   ├── settings/              # base.py, development.py, production.py, test.py
│   ├── urls.py                # Root URL routing
│   ├── context_processors.py  # nav_current, unread_notifications, currency_context
│   └── wsgi.py / asgi.py      # Production entry points
├── templates/
│   ├── base.html              # Main layout (sidebar + bottom nav + main)
│   ├── components/            # 14 reusable design system partials
│   ├── pages/                 # Full pages (home, dashboard, styleguide, errors)
│   ├── account/               # Allauth overrides (login, signup, logout)
│   ├── accounts/              # Profile, onboarding, risk quiz
│   ├── portfolio/             # Portfolio list & detail
│   ├── real_estate/           # 9 main templates + 14 partials (26 total)
│   ├── education/             # Learning path, lesson, quiz templates
│   ├── scenarios/             # Lab landing page (stub)
│   └── impact/                # Directory landing page (stub)
├── frontend/
│   ├── src/styles/main.css    # Tailwind v4 @theme (design tokens) + components
│   ├── src/main.js            # Vite entry point (HTMX, Alpine, chart init)
│   ├── src/charts/            # allocation.js, evolution.js, performance.js, scenario.js
│   ├── vite.config.js         # Vite build config
│   └── package.json           # Vite 6, Tailwind v4, Chart.js, Alpine, HTMX
├── locale/
│   └── fr/LC_MESSAGES/        # French translations (~614 entries, 2617 lines)
├── instructions/
│   ├── Limpid_Design_Proposals.md
│   ├── Design_System_Implementation_Plan.md
│   ├── Limpid_Crescendo_EN_v1/  # 18 lessons + quizzes (EN)
│   └── Limpid_Crescendo_FR_v1/  # 18 lessons + quizzes (FR)
├── docs/
│   ├── plans/                 # Implementation plans (.md) + done/ archive
│   └── research/              # This file
├── .claude/
│   ├── plans/                 # Claude Code plan files
│   ├── settings.json          # Pre-commit hooks, SSH permissions
│   └── settings.local.json    # Developer-specific overrides
├── scripts/
│   ├── setup-rpi.sh           # One-time RPi provisioning
│   ├── deploy.sh              # Redeploy on RPi
│   └── seed_all.sh            # Seed all data (securities, education, impact)
├── deploy/
│   └── compose.prod.yml       # Production Docker Compose (3 services)
├── Containerfile              # Multi-stage: Node (frontend) → Python (app)
├── compose.yml                # Local dev stack (db + web)
├── pyproject.toml             # Python deps, ruff, pytest config
├── .pre-commit-config.yaml    # Ruff pre-commit hooks
├── conftest.py                # pytest fixtures (user, client)
└── CLAUDE.md                  # Project guide & conventions
```

---

## 4. Django Configuration

### Settings (split across 4 files)

**base.py** — Shared settings:
- 8 custom apps + allauth + django_htmx + django_vite + django.contrib.humanize
- 11 middleware: Security, WhiteNoise, Session, Locale, Common, CSRF, Auth, Allauth, Messages, XFrame, HTMX
- PostgreSQL by default (`postgres://limpid:limpid@localhost:5432/limpid`)
- French primary language, EN/FR bilingual, America/Toronto timezone
- Allauth: email login only, email verification optional, login redirect to `/dashboard/`
- Django Vite: manifest-based, dev server on localhost:5173
- 3 custom context processors: `nav_current`, `unread_notifications`, `currency_context`
- SITE_ID = 1 (required by django-allauth)
- BigAutoField as default auto field
- 4 password validators (similarity, length, common, numeric)

**development.py** — Adds:
- DEBUG=True, ALLOWED_HOSTS=["*"]
- django-debug-toolbar + django-browser-reload
- Console email backend
- Vite dev_mode=True (HMR)
- Simple StaticFilesStorage (no compression)
- Insecure default SECRET_KEY for dev only

**production.py** — Adds:
- DEBUG=False, SECRET_KEY required from env (no default)
- HSTS (1 year), secure cookies, X-Forwarded-Proto
- CSRF_TRUSTED_ORIGINS configurable via env
- USE_X_FORWARDED_HOST=True for Cloudflare

**test.py** — Adds:
- In-memory SQLite for speed
- MD5PasswordHasher (fast, not secure — fine for tests)
- Vite dev_mode=True (skip manifest check)
- Silences django_vite.W001
- locmem EmailBackend

### URL Routing

| Prefix | App | Description |
|--------|-----|-------------|
| `/` | accounts (home) | Landing page |
| `/dashboard/` | portfolio | Main investment dashboard |
| `/accounts/` | allauth + accounts | Auth, profile, onboarding, risk quiz |
| `/portfolio/` | portfolio | Portfolio list & detail |
| `/market/` | market_data | Market data (currently empty views) |
| `/transparency/` | transparency | Transparency reports (not implemented) |
| `/learn/` | education | Learning path, lessons, quizzes |
| `/scenarios/` | scenarios | Scenario lab (scaffolded) |
| `/impact/` | impact | Impact directory (scaffolded) |
| `/real-estate/` | real_estate | Real estate patrimony management |
| `/admin/` | django.contrib.admin | Django admin |
| `/i18n/` | django.conf.urls.i18n | Language switching |
| `/styleguide/` | accounts (DEBUG) | Design system reference |

**Debug-only routes**: `__debug__/` (django-debug-toolbar), `__reload__/` (django-browser-reload)

### Context Processors

**nav_current** — Maps request path to active nav section string for sidebar/bottom nav styling:
- `/dashboard*` → "dashboard", `/portfolio*` → "portfolios", `/learn*` → "learn"
- `/scenarios*` → "scenarios", `/impact*` → "impact", `/real-estate*` → "real_estate"
- `/real-estate/notifications*` → "notifications", `/accounts/profile*` → "profile", `/` → "home"

**unread_notifications** — Counts unread `PropertyNotification` objects for authenticated user. Injected as `unread_notification_count`. Returns 0 for unauthenticated users.

**currency_context** — Reads `display_currency` from session. Used by `{% show_money %}` template tag for multi-currency conversion.

---

## 5. Apps — Detailed Analysis

### 5.1 accounts (FULLY IMPLEMENTED)

**Models (2):**
- **UserProfile** (OneToOne → User): province (13 CA provinces/territories), preferred_language (FR/EN, default FR), risk_profile_score (1-10, nullable), onboarding_completed (bool)
  - Property: `risk_profile_label` → Conservative (1-3), Moderate (4-6), Growth (7-10)
  - `__str__` → "Profile of {user.email}"
- **RiskQuizResponse** (FK → User): question_key (6 questions), answer_value (1-4 scale). Unique on (user, question_key)

**Views (8 functions):**
- `home_view` — Landing page, redirects auth users to dashboard
- `profile_view` — GET/POST for user profile (province + language), shows risk profile score. Auto-creates UserProfile via `get_or_create()`
- `onboarding_view` / `onboarding_step(step)` — 3-step HTMX wizard: province → language → summary → create sandbox portfolio + redirect to dashboard. Redirects to dashboard if already completed.
- `risk_quiz_view` / `risk_quiz_step(step)` / `risk_quiz_results` — 6-question HTMX quiz with immediate answer feedback. Uses `update_or_create()` for idempotent responses.
- `styleguide_view` — Design system reference (DEBUG only, 404 in prod)

**HTMX Flow — Onboarding:**
```
/accounts/onboarding/ (GET)
  → renders onboarding.html with step 1 form
  → user submits province
/accounts/onboarding/step/1/ (POST)
  → saves province, returns step 2 partial via hx-target="#onboarding-content"
  → user submits language
/accounts/onboarding/step/2/ (POST)
  → saves language, returns step 3 summary partial
  → user clicks "Go to dashboard"
/accounts/onboarding/step/3/ (GET)
  → marks onboarding_completed=True, creates sandbox portfolio, redirects to /dashboard/
```

**HTMX Flow — Risk Quiz:**
```
/accounts/risk-quiz/ (GET)
  → renders quiz_step for question 1
  → user answers, clicks "Next"
/accounts/risk-quiz/step/1/ (POST)
  → saves response via update_or_create, returns quiz_step for question 2
  ... questions 2-5 similarly ...
/accounts/risk-quiz/step/6/ (POST)
  → saves final response, calls risk_quiz_results()
  → aggregates all responses, calculates score (1-10), renders result partial
```

**Services (116 lines):**
- `QUIZ_QUESTIONS` — 6 questions with 4 MCQ choices each (investment_knowledge, time_horizon, risk_comfort, loss_reaction, income_stability, return_expectation)
- `calculate_risk_score(responses)` — Normalizes raw sum (6-24) to 1-10 scale via: `round((total - min) / (max - min) * 9) + 1`, clamped to [1, 10]
- `get_risk_profile_label(score)` — Conservative / Moderate / Growth
- `get_risk_profile_description(score)` — Localized educational paragraph

**Forms (4):** ProfileForm (province, language), OnboardingStep1Form (province), OnboardingStep2Form (language). All use `TAILWIND_SELECT_CLASS = "input"`.

**Admin:** UserProfile (list: user, province, language, score, onboarding_completed; filter: province, language, onboarding_completed) and RiskQuizResponse (list: user, question_key, answer_value; filter: question_key).

**Tests: 31 tests** (test_models: 11, test_views: 12, test_services: 8)
- Models: create profile, str, risk_profile_label boundaries, quiz response uniqueness
- Views: home page, profile CRUD with auto-create, onboarding 3-step flow, quiz full lifecycle
- Services: risk score calculation (empty/min/max/moderate), profile labels

---

### 5.2 portfolio (PARTIAL IMPLEMENTATION)

**Models (3):**
- **Portfolio** (FK → User): name, is_sandbox (bool), created_at
- **Holding** (FK → Portfolio + Asset): quantity (4 decimal), average_cost
  - Properties: market_value, total_cost, gain_loss, gain_loss_pct
- **Transaction** (FK → Portfolio + Asset): transaction_type (buy/sell), quantity, price, fees, executed_at

**Views (3 functions):**
- `dashboard_view` — Main dashboard: snapshot, allocation chart, exposures, clarity score, next lesson. Auto-redirects to onboarding if no portfolio.
- `portfolio_list` — User portfolios (redirects to detail if only 1)
- `portfolio_detail` — Detail: snapshot, allocation chart, holdings table (8 columns), recent 20 transactions

**Services (277 lines):**
- `SANDBOX_ALLOCATIONS` — Predefined by risk tier:
  - Conservative: 60% XBAL + 30% ZAG + 10% CASH
  - Moderate: 50% XEQT + 25% XBAL + 15% ZAG + 10% RY
  - Growth: 60% XEQT + 20% VFV + 10% SHOP + 10% RY
- `create_sandbox_portfolio(user)` — Idempotent creation based on risk score
- `get_portfolio_snapshot(portfolio)` — total_value, total_cost, gain_loss, daily_change with formatting
- `get_allocation_breakdown(portfolio)` — By asset type, with JSON chart data (8-color palette)
- `get_exposure_breakdown(portfolio)` — Geography + sector percentage bars
- `get_clarity_score(user, portfolio)` — % of asset types user has learned about (via ASSET_TYPE_LESSON_MAP)
- `get_holdings_table(portfolio)` — Sorted holdings with all metrics

**Templates:** List (card grid with sandbox badge), detail (holdings table, allocation doughnut chart, recent transactions).

**Admin:** Portfolio, Holding (filterable by asset_type), Transaction.

**Tests:** None. **Forms:** Empty.

---

### 5.3 market_data (SCAFFOLD + SEED DATA)

**Models (1):**
- **Asset**: ticker (unique), name, asset_type (etf/stock/bond/gic/cash), currency (CAD/USD), sector, geography, current_price, previous_close, description
  - Properties: daily_change, daily_change_pct

**Management command:** `seed_assets` — Creates/updates 7 Canadian assets: XEQT, XBAL, ZAG, VFV, RY, SHOP, CASH (hardcoded prices + descriptions). Idempotent via `update_or_create`.

No views, no URLs — data accessed via portfolio app.

**Admin:** Asset with list_display (ticker, name, type, currency, price), list_filter (asset_type, currency, geography), search_fields (ticker, name).

**Tests:** None

---

### 5.4 education (FULLY IMPLEMENTED)

**Models (3):**
- **LessonProgress** (FK → User): lesson_id (str), completed_at. Unique on (user, lesson_id)
- **QuizResponse** (FK → User): lesson_id, question_id, choice_id, is_correct (bool), answered_at. Unique on (user, lesson_id, question_id)
- **QuizCompletion** (FK → User): lesson_id, score, total, completed_at. Unique on (user, lesson_id)

**Views (6 functions):**
- `learning_path` — Overview with progress summary by level
- `lesson_detail(lesson_id)` — Renders markdown lesson with frontmatter (title, level, duration, tags, key_terms, prerequisites), shows completion/quiz status
- `mark_lesson_complete(lesson_id)` — HTMX POST toggle (create/delete LessonProgress)
- `quiz_start(lesson_id)` — Quiz shell, clears previous responses for fresh attempt
- `quiz_step(lesson_id, step)` — HTMX POST/GET for answer submission + immediate feedback with explanation
- `quiz_next(lesson_id, step)` — Advances to next question or shows results, auto-completes lesson on finish

**Services (202 lines):**
- `CURRICULUM_DIRS` — Maps language → Path to lesson directory
- `load_curriculum_index(lang)` — Parses curriculum_index.json (cached)
- `load_glossary(lang)` — Loads glossary JSON (cached)
- `_parse_frontmatter(text)` — Extracts YAML-like metadata from markdown (supports key-value pairs and lists)
- `_load_lesson_raw` / `load_lesson` — Loads .md → HTML (markdown.markdown, LRU cached maxsize=64)
- `load_quiz(lesson_id, lang)` — Loads quiz JSON (cached)
- `get_lesson_titles(lang)` — All lesson IDs → titles
- `get_user_progress_summary(user, lang)` — Progress by level with lesson list and quiz scores
- `get_next_lesson(user, lang)` — First uncompleted lesson or None

**Admin:** LessonProgress, QuizResponse, QuizCompletion with list_display/filter.

**Tests:** None

---

### 5.5 real_estate (FULLY IMPLEMENTED — Most Complex App)

**Models (15):**

| Model | Fields | Key Relationships |
|-------|--------|-------------------|
| **Property** | name, **country** (CA/FR), property_type (8 types: house, condo, condo_undivided, duplex, triplex, land, cottage, commercial), usage (4 types: primary, secondary, rental, commercial), address, city, province, postal_code, currency (CAD/EUR), purchase_price, purchase_date, welcome_tax_paid, notary_fees_purchase, current_valuation, valuation_date, municipal_assessment | M2M → User through PropertyOwnership |
| **PropertyOwnership** | is_admin, down_payment, joined_at | FK → User, FK → Property. Unique(user, property) |
| **OwnershipPeriod** | start_date, end_date (nullable=ongoing), note | FK → Property. Ordered by start_date |
| **OwnershipPeriodShare** | share_pct | FK → OwnershipPeriod, FK → PropertyOwnership. Unique(period, owner) |
| **Mortgage** | lender, principal, annual_rate, rate_type (fixed/variable/**mixed**), amortization_years (25), term_years (5), payment_frequency (monthly/biweekly/accelerated_biweekly), start_date, is_active, insurance_premium, **borrower_insurance_rate** | FK → Property (named `real_estate` to avoid `@property` shadow). Ordered by -start_date |
| **MortgageRateChange** | new_annual_rate, new_rate_type, effective_date, **is_simulation** (bool), note | FK → Mortgage. Ordered by effective_date. Indexed for performance |
| **MortgagePayment** | payment_number, date, total_payment, principal_portion, interest_portion, balance_after | FK → Mortgage, FK → PropertyOwnership (paid_by, nullable). Unique(mortgage, payment_number) |
| **OwnerMonthlyPayment** | monthly_amount, effective_date, note | FK → Mortgage, FK → PropertyOwnership (owner). Unique(mortgage, owner, effective_date) |
| **PropertyExpense** | expense_type (6 CA + 2 FR types), description, amount, date, increases_acb, **proof_link** (URL, optional) | FK → Property, FK → PropertyOwnership (paid_by). Ordered by -date |
| **PropertyValuation** | value, date, source (manual/appraisal/municipal/comparable), note | FK → Property. Ordered by -date |
| **PropertyTax** | tax_type (2 CA + 3 FR types), year, amount | FK → Property. Unique(property, tax_type, year). Ordered by -year, tax_type |
| **RentalIncome** | monthly_rent, agency_fee_pct, start_date, end_date (nullable), note | FK → Property (named `real_estate`). Property: net_monthly_rent |
| **PropertyInvitation** | email, down_payment, share_pct (default=50), token (unique 64-char), accepted | FK → Property, FK → User (invited_by) |
| **PropertyNotification** | verb (14 types), description, is_read, created_at | FK → Property, FK → User (recipient), FK → User (actor), FK → PropertyInvitation (nullable). Indexed on [recipient, is_read, -created_at] |

**Property computed properties:**
- `total_invested` — purchase_price + welcome_tax_paid + notary_fees_purchase + sum of capital improvement expenses
- `total_appreciation` — current_valuation - purchase_price
- `total_appreciation_pct` — (current_valuation / purchase_price - 1) × 100

**Mortgage computed properties:**
- `effective_principal` — principal + insurance_premium
- `monthly_rate` — **Country-dependent**: Canada fixed uses semi-annual compounding `(1+r/2)^(1/6)-1`, Canada variable and all France mortgages use simple `r/12`
- `monthly_payment` — Standard amortization formula PMT + monthly borrower insurance if set

**RentalIncome computed properties:**
- `net_monthly_rent` — monthly_rent × (1 - agency_fee_pct / 100)

**Views (30 functions):**

*List & Detail:*
- `property_list` — Lists user's properties with per-owner snapshots and monthly costs
- `property_detail` — Full property dashboard: snapshot, owner_snapshot, shares, sale_estimate, 3 chart JSONs, taxes, pending invitations, country-aware TERM_TOOLTIPS, "Total vs My share" Alpine toggle
- `property_create` — PropertyForm + MortgageForm (prefix), creates OwnershipPeriod + shares, optionally PropertyInvitation for co-owner
- `property_edit` — PropertyForm + MortgageForm, notifies co-owners on change
- `delete_property` — Admin-only, redirects to list

*HTMX CRUD — Expenses:*
- `add_expense` / `edit_expense` / `delete_expense` — HTMX partial responses, triggers "expenses-changed" event, notifies co-owners

*HTMX CRUD — Taxes:*
- `add_tax` / `edit_tax` / `delete_tax` — Unique constraint validation per (property, tax_type, year), notifies co-owners

*HTMX CRUD — Valuations:*
- `add_valuation` / `edit_valuation` / `delete_valuation` — Updates property.current_valuation & valuation_date, notifies co-owners

*Amortization & Financials:*
- `amortization_view` — Full amortization schedule with per-owner breakdowns (if co-owners), yearly ownership evolution table, current month highlighting with auto-scroll JS
- `sale_simulator` — Sale proceeds estimation with optional sale_price & commission % query params

*Mortgage Management:*
- `add_rate_change` — Add MortgageRateChange (renewal or simulation), triggers "mortgage-changed"
- `delete_rate_change` — Delete rate change

*Per-Owner Payment Customization:*
- `owner_payments` — View/create OwnerMonthlyPayment custom splits; auto-calculates co-owner's portion for 2-owner properties
- `edit_owner_payment` / `delete_owner_payment` — Update custom payment splits

*Rental Income:*
- `add_rental_income` — Add RentalIncome entry, triggers "rental-changed"
- `delete_rental_income` — Remove entry

*Co-Ownership & Invitations:*
- `invite_co_owner` — Creates PropertyInvitation with random 64-char token, notifies co-owners
- `accept_invitation` — Token-based email validation, creates ownership, updates period shares, notifies
- `accept_invitation_htmx` / `decline_invitation_htmx` — HTMX versions from notification center with cleanup
- `remove_co_owner` — Ends current period, creates new period, redistributes shares equally, notifies

*Utilities:*
- `manage_ownership_periods` — Lists all periods with prefetched shares
- `notification_list` / `mark_notifications_read` — Notification center with select_related prefetching
- `monthly_cost_partial` — HTMX endpoint for recalculating monthly costs on events
- `charts_partial` — HTMX endpoint for regenerating JSON chart data (equity, payment breakdown, expenses by type)
- `toggle_currency` — Session-based currency toggle (None ↔ target)

**Services (684 lines — Financial math engine):**

*Amortization:*
- `calculate_monthly_rate(annual_rate, rate_type, country)` — Canada fixed: `(1+r/2)^(1/6)-1`, Canada variable + all France: `r/12`
- `calculate_monthly_payment(principal, annual_rate, amort_years, rate_type, country)` — Standard PMT formula
- `generate_amortization_schedule(mortgage)` — Full 300+ payment schedule with rate change support; handles zero rates; includes monthly borrower insurance for France; adjusts final payment for rounding; returns list of dicts with payment_number, date, total_payment, principal, interest, insurance, balance, annual_rate

*Balance & Payoff:*
- `get_remaining_balance(mortgage, as_of_date)` — Interpolates from schedule
- `get_total_paid(mortgage, as_of_date)` — Returns {total_principal_paid, total_interest_paid, total_paid}

*Ownership:*
- `get_current_ownership_shares(prop, as_of_date)` — Gets OwnershipPeriodShare for active period, fallback to equal split if no periods exist
- `get_owner_contributions(ownership)` — Sums down_payment + mortgage principal paid + expenses paid
- `get_ownership_comparison(prop)` — Per-owner breakdown: purchase_share (down payment ratio) vs contribution_share (total contributions ratio) vs admin_share
- `get_owner_snapshot(prop, user)` — Per-owner metrics (share × property values), principal_paid from amortization schedule (not MortgagePayment records)
- `get_property_snapshot(prop)` — current_valuation, appreciation, appreciation_pct, mortgage_balance, equity, equity_pct, monthly_payment

*Sale simulation:*
- `estimate_sale_proceeds(prop, sale_price, commission, notary)` — Full sale simulation with country dispatch:
  - **Canada**: Commission + GST/QST (14.975%), capital gains 50% inclusion × 45% marginal for non-primary
  - **France**: Commission + TVA (20%), plus-value immobilière with complex abatement system
  - Returns: {sale_price, mortgage_balance, gross_equity, agent_commission, notary_fees, capital_gains_tax, total_costs, net_proceeds, per_owner[], capital_gains_details}
- `_calculate_acb(prop)` — Adjusted cost base: purchase + taxes + fees + capital improvements (expenses with `increases_acb=True`)

*French capital gains tax (complex):*
- `_calculate_french_capital_gains_tax(prop, sale_price)` — Primary residence always exempt. Rental properties subject to:
  - **19% income tax** with abatements: 6%/year from year 6-20, 4% at year 21, full exemption at 22+
  - **17.2% social contributions** with abatements: 1.65%/year from year 6-21, 1.6% at year 22, 9%/year from year 23-30, full exemption at 30+
  - **Surtax** on gains >50k: tiered 2-6% with smoothing brackets
- `_calculate_french_surtax(taxable_gain)` — 6-tier progressive surtax (50k-260k+)

*Per-Owner Amortization:*
- `generate_per_owner_amortization(mortgage)` — Returns (schedule, owner_summaries):
  - Schedule: full amortization with additional "owner_payments" dict per entry showing each owner's principal/interest/payment
  - Uses OwnershipPeriodShare & OwnerMonthlyPayment to split payments based on custom amounts or ownership percentages
  - Owner summaries: {owner, principal_paid, interest_paid, total_paid, contribution_pct}

*Monthly Cost Analysis:*
- `calculate_monthly_cost(prop, for_user=None)` — Breaks down total costs:
  - Mortgage: active mortgages' monthly_payment
  - Taxes: latest year's taxes ÷ 12
  - Recurring: last 12 months of condo_fees/charges_copro/insurance ÷ 12
  - Rental: latest active/most recent RentalIncome (net_monthly_rent)
  - Returns: {mortgage_payment, taxes_monthly, recurring_expenses_monthly, rental_income, rental_net, total_monthly}
  - If for_user: applies ownership share % + custom OwnerMonthlyPayment splits

*Charting:*
- `generate_evolution_chart_data(mortgage)` — Time series: {labels, principal_series, interest_series, balance_series, payment_series, current_month_index}

*Notifications:*
- `notify_co_owners(prop, actor, verb, description)` — Broadcasts PropertyNotification to all co-owners except actor

**Signals (`signals.py`):**
- `@receiver(user_logged_in)` — On login, finds pending PropertyInvitations matching user's email (not yet accepted), creates PropertyNotification for each if not already notified. Enables co-owners to see pending invitations immediately on login.

**Template Tags (`real_estate_filters.py`):**
- `money(value, currency)` — Formats as `$1,234.56` or `€1,234.56` with manual comma thousands separators
- `cad(value)` — Backward-compatible alias: `money(value, "CAD")`
- `show_money(context, value, native_currency)` — Context-aware simple_tag: reads `display_currency` from session, converts via exchange rates if different from native, then formats
- `other_currency(currency)` — Returns the alternate currency: CAD→EUR, EUR→CAD
- `convert_to(value, args)` — Filter for explicit conversion: `{{ amount|convert_to:"CAD,EUR" }}`
- `signed_pct(value)` — Formats percentage with `+` prefix for positive values
- `dictkey(d, key)` — Safe dict[key] access in templates

**Exchange Rates (`exchange_rates.py`):**
- Fetches from `open.er-api.com/v6/latest/CAD`, caches 1 hour in Django cache
- Fallback hardcoded rates: CAD→EUR = 0.67, EUR→CAD = 1.49
- `convert(amount, from_currency, to_currency)` — Returns converted Decimal or None

**Tooltips (`tooltips.py`) — Country-aware:**
- `TERM_TOOLTIPS` — Base dictionary with ~26 educational tooltip texts for common financial terms (value, equity, mortgage, your_share, purchase_price, appreciation, monthly_cost, etc.)
- `TERM_TOOLTIPS_CA` — Canada-specific overrides (4): amortization, agent_commission, capital_gains_tax, insurance_premium
- `TERM_TOOLTIPS_FR` — France-specific overrides (7+): amortization, agent_commission, capital_gains_tax, borrower_insurance_rate, frais_notaire, taxe_foncière, taxe_habitation, IFI
- `get_tooltips(country="CA")` — Merges base + country-specific dicts

**Forms (10):**
- **PropertyForm** — Full property fields + extra co-owner fields + FIELD_TOOLTIPS. Country-aware: dynamically relabels province→Département, welcome_tax→Frais de notaire, notary_fees→Frais d'agence, municipal_assessment→Valeur cadastrale when country=FR. Includes full 96-département dropdown for France.
- **MortgageForm** — All optional (prefix="mortgage"), accepts `country` kwarg for label/tooltip adjustments
- **PropertyTaxForm** — Country-aware: Canada types [municipal, school], France types [taxe_foncière, taxe_habitation, ifi]
- **ExpenseForm** — expense_type, description, amount, date, increases_acb checkbox, proof_link (URL)
- **ValuationForm** — value, date, source, note
- **InviteCoOwnerForm** — email, down_payment
- **RateChangeForm** — new_annual_rate, new_rate_type, effective_date, is_simulation, note
- **RentalIncomeForm** — monthly_rent, agency_fee_pct, start_date, end_date (optional), note
- **OwnerMonthlyPaymentForm** — owner (queryset filtered to property ownerships with custom label_from_instance), monthly_amount, effective_date, note
- All use `TAILWIND_INPUT_CLASS = "input"`

**Admin:** All 15 models registered with list_display, list_filter, search_fields. PropertyAdmin has inlines for PropertyOwnership and Mortgage. RentalIncomeAdmin, OwnerMonthlyPaymentAdmin, MortgageRateChangeAdmin all registered.

**URLs (34 patterns):**
```
/real-estate/                                                          → property_list
/real-estate/create/                                                   → property_create
/real-estate/notifications/                                            → notification_list
/real-estate/notifications/mark-read/                                  → mark_notifications_read
/real-estate/<pk>/                                                     → property_detail
/real-estate/<pk>/edit/                                                → property_edit
/real-estate/<pk>/delete/                                              → delete_property
/real-estate/<pk>/expense/                                             → add_expense
/real-estate/<pk>/expense/<expense_id>/edit/                           → edit_expense
/real-estate/<pk>/expense/<expense_id>/delete/                         → delete_expense
/real-estate/<pk>/valuation/                                           → add_valuation
/real-estate/<pk>/valuation/<valuation_id>/edit/                       → edit_valuation
/real-estate/<pk>/valuation/<valuation_id>/delete/                     → delete_valuation
/real-estate/<pk>/tax/                                                 → add_tax
/real-estate/<pk>/tax/<tax_id>/edit/                                   → edit_tax
/real-estate/<pk>/tax/<tax_id>/delete/                                 → delete_tax
/real-estate/<pk>/mortgage/<mortgage_id>/amortization/                 → amortization_view
/real-estate/<pk>/mortgage/<mortgage_id>/rate-change/                  → add_rate_change
/real-estate/<pk>/mortgage/<mortgage_id>/rate-change/<rc_id>/delete/   → delete_rate_change
/real-estate/<pk>/mortgage/<mortgage_id>/owner-payments/               → owner_payments
/real-estate/<pk>/mortgage/<mortgage_id>/owner-payment/<id>/edit/      → edit_owner_payment
/real-estate/<pk>/mortgage/<mortgage_id>/owner-payment/<id>/delete/    → delete_owner_payment
/real-estate/<pk>/sale-simulator/                                      → sale_simulator
/real-estate/<pk>/invite/                                              → invite_co_owner
/real-estate/<pk>/remove-owner/<ownership_id>/                         → remove_co_owner
/real-estate/invite/<token>/accept/                                    → accept_invitation (token)
/real-estate/invitation/<invitation_id>/accept/                        → accept_invitation_htmx
/real-estate/invitation/<invitation_id>/decline/                       → decline_invitation_htmx
/real-estate/<pk>/ownership-periods/                                   → manage_ownership_periods
/real-estate/<pk>/monthly-cost/                                        → monthly_cost_partial (HTMX)
/real-estate/<pk>/charts/                                              → charts_partial (HTMX)
/real-estate/<pk>/rental-income/                                       → add_rental_income
/real-estate/<pk>/rental-income/<income_id>/delete/                    → delete_rental_income
/real-estate/currency/toggle/                                          → toggle_currency
```

**Tests: ~90+ tests** across 4 files:
- test_models.py (~15): Property str/appreciation/invested, Mortgage rates/payments/zero-rate (CA + FR), RateChange ordering, RentalIncome net_monthly_rent, OwnerMonthlyPayment uniqueness, expense proof_link
- test_services.py (~40+): Monthly rate/payment (CA + FR), amortization schedule/balance/paid, rate change application, borrower insurance in schedule, French capital gains with full abatement tiers, French surtax boundary cases, ownership shares with period transitions, contributions, comparison (purchase_share vs contribution_share), snapshots, sale simulation (CA + FR), ACB, per-owner amortization, monthly cost (full + per-user), evolution chart data, notifications
- test_views.py (~30+): CRUD, HTMX endpoints, invitation lifecycle (create, token accept, HTMX accept/decline), co-owner creation/removal with share redistribution, notification views, currency toggle, French property creation with mortgage + taxes, French amortization with insurance, rate changes, rental income, owner payments, property deletion
- test_filters.py (4): money formatting with commas, currency conversion, signed_pct, dictkey

---

### 5.6 transparency (NOT IMPLEMENTED)

Completely empty — no models, views, URLs, or templates. App skeleton only.

### 5.7 scenarios (SCAFFOLDED)

Single view `scenario_lab` rendering a landing page. No models, no logic.

### 5.8 impact (SCAFFOLDED)

Single view `directory` rendering a landing page. No models, no logic.

---

## 6. Design System — "Clair & calme" (v2: "Quiet Precision")

### Philosophy
- Serious yet warm — "medical/engineering tool" precision paired with serenity
- Every financial figure should be explainable (tooltip + link to learning)
- Actions are conscious ("Understand" / "Explore"), not aggressive
- Mobile-first: mobile for reading/education, desktop for dashboard analysis
- Typographic hierarchy is the design — depth through light, not shadow
- Motion as feedback (hovers, HTMX animations, staggered page entrance)

### Theme Tokens (Tailwind v4 `@theme` in `frontend/src/styles/main.css`)

| Token | Value | Usage |
|-------|-------|-------|
| `font-sans` | Geist (system fallback) | Body text throughout |
| `font-mono` | Geist Mono (ui-monospace fallback) | Numbers, financial data |
| `primary-50..900` | Custom warm indigo (#f0f0ff → #2e2c78) | Accent color throughout |
| `bg-base` | #fafaf9 | Page background (warm off-white) |
| `bg-card` | #ffffff | Card/panel/nav background |
| `bg-elevated` | #ffffff | Elevated surfaces |
| `bg-subtle` | #f5f5f4 | Muted backgrounds, hover states |
| `bg-hover` | #f5f5f4 | Interactive hover states |
| `text` | #1c1917 | Primary text (warm dark) |
| `text-muted` | #78716c | Secondary text (warm gray) |
| `text-faint` | #a8a29e | Tertiary text (light gray) |
| `border` | #e7e5e4 | Default border |
| `border-strong` | #d6d3d1 | Stronger separation |
| `success-*` | Green family (#f0fdf4 → #15803d) | Positive states (gains, confirmation) |
| `warning-*` | Amber family (#fffbeb → #b45309) | Caution states (pending, disclaimer) |
| `danger-*` | Red family (#fef2f2 → #b91c1c) | Negative states (losses, errors) |

**Key constraint**: Never use raw Tailwind utilities (blue-600, gray-500) for themed elements — always use design tokens.

### Typography
- **Fonts**: Geist Sans (body) + Geist Mono (numbers), loaded from CDN (`cdn.jsdelivr.net/npm/geist@1.3.1`)
- **Base size**: 0.9375rem (15px), line-height 1.6
- **Headings**: letter-spacing -0.025em, font-weight 600
- **Monospace**: `font-variant-numeric: tabular-nums` for aligned columns

### Custom CSS (`@layer base` + `@layer components`)

**Base layer:**
- `[x-cloak] { display: none !important }` — Prevents Alpine flash of unstyled content
- Body typography: Geist font, warm colors, -webkit-font-smoothing antialiased
- All interactive elements: 150ms ease transitions on color, bg, border, box-shadow
- HTMX animations: `.htmx-added` (fadeIn 200ms), `.htmx-settling` (opacity 0)
- Staggered entrance: `.animate-enter > *` with 50ms delays per child (fadeSlideUp 300ms, 6-child cascade)

**Component classes:**
- `.btn-primary` — Indigo button with hover lift (-1px translateY) + indigo shadow
- `.btn-ghost` — Transparent button with hover bg-hover
- `.btn-danger` — Red variant of btn-primary
- `.input` — Rounded-xl border with focus ring (primary-400 border + primary-100 ring)
- `.input-error` — Danger variant for validation errors
- `.card-interactive` — Hover: border-strong + shadow-md + translateY(-2px)
- `.badge-notification` — 2s pulse animation (opacity 0.7 at 50%)
- `.animate-toast-in` — Slide up + fade in (300ms) for flash messages

**Custom utilities:**
- `container-limpid` — max-width 1200px, auto margins, responsive padding (1rem/1.5rem at sm)
- `safe-area-bottom` — `padding-bottom: env(safe-area-inset-bottom)` for mobile notch devices

**Prose styles** — Styled markdown rendering: h2, h3, blockquotes, lists, inline code, pre blocks with proper typography.

### Reusable Components (`templates/components/`)

All use a **start/end pattern** for slotted content:

| Component | Props | Usage |
|-----------|-------|-------|
| `card_start/end` | title, variant, icon, tooltip_id, tooltip_text | Wrapper card (default/warning/success/elevated). Tooltip rendered adjacent to `<h3>` title |
| `stat_card` | label, value, annotation, tooltip_id, tooltip_text | Single metric card (1.75rem monospaced value). Uses `<div>` (not `<p>`) to allow block-level tooltip |
| `badge` | label, variant | Inline label (primary/success/warning/danger/neutral) with ring-1 |
| `callout_start/end` | type, title | Educational callout (info/warning/example/impact) with 3px left border accent |
| `metric_row` | label, value, annotation, tooltip_id, tooltip_text | Key-value display row with border-b separator. Uses `<div>` (not `<dt>/<dd>`) |
| `tooltip` | id, text | Help popover (desktop) / bottom-sheet (mobile). Alpine.js dual-mode with global close-tooltips event |
| `progress_bar` | current, total | Step indicator with percentage fill and "Step X of Y" text |
| `empty_state` | icon, title, description, action_url, action_label | Centered empty state with optional CTA button |
| `nav` | — | Desktop sidebar navigation (w-56 fixed), 7 nav items, notification badge, auth section |
| `bottom_nav` | — | Mobile bottom navigation (fixed, md:hidden), 5 items, safe-area-bottom |
| `disclaimer_banner` | — | Dismissible amber "not financial advice" banner (Alpine x-data) |
| `footer` | — | Copyright, disclaimer, language switcher, pb-20 on mobile for bottom nav clearance |
| `lang_switcher` | — | FR / EN toggle (POST forms to Django set_language) |

### Tooltip System (Alpine.js)

The tooltip component (`templates/components/tooltip.html`) provides educational help on financial terms:

**Architecture:**
- Outer `<span>` with `x-data="{ open: false }"` + `@close-tooltips.window` listener
- `?` button with `@click.stop` that dispatches `close-tooltips` event then toggles
- Desktop: Absolute positioned popover (hidden below md, `md:block`)
- Mobile: Fixed bottom-sheet with backdrop overlay + "Got it" dismiss button
- All popover elements use `x-cloak` to prevent flash before Alpine init
- Text reset: `normal-case tracking-normal font-normal` to prevent inheriting parent styles (uppercase, tracking-wide from stat cards/metric rows)

**Key design decision:** Tooltip inner elements use `<span>` (not `<div>`) because the tooltip is often placed inside phrasing content. The `card_start.html` moves the tooltip outside the `<h3>` into a sibling `<div>` to maintain valid HTML.

### Navigation
- **Desktop**: Fixed left sidebar (w-56), 7 icon+label items, active state = left 3px indigo bar + text-primary-700
- **Mobile**: Fixed bottom nav (5 items), stacked icon+label, active = 1px indigo dot + text-primary-600
- **Auth section**: Profile link + Logout (authenticated) or Login + Sign up (anonymous)
- **Notification badge**: red circle (h-4 w-4) with count, pulse animation, in both sidebar and bottom nav
- **Language switcher**: In sidebar + footer
- **Disclaimer banner**: Alpine.js dismissible, amber styling

### Layout (base.html)
- FOUC prevention: `visibility:hidden` until Vite CSS loads, revealed in main.js
- HTMX config: `defaultSwapStyle="innerHTML"`, CSRF token in body via `hx-headers`
- Sidebar offset: `md:pl-56` on main content wrapper
- Messages: color-coded flash messages with auto-dismiss (5s) via Alpine `x-init="setTimeout(() => show = false, 5000)"`
- Footer: extra `pb-20` on mobile to clear bottom nav

---

## 7. Frontend Build Pipeline

### Vite Configuration (`frontend/vite.config.js`)
- **Plugin**: @tailwindcss/vite (handles Tailwind v4 compilation)
- **Entry**: `frontend/src/main.js`
- **Output**: `static/dist/` with `.vite/manifest.json`
- **Base path**: `/static/` (matches Django STATIC_URL)
- **Dev server**: localhost:5173 with HMR, origin configured
- **Build**: `emptyOutDir: true` to clean output before build

### main.js — Entry Point
1. Imports `styles/main.css` (Tailwind + theme)
2. Reveals page after CSS injection (FOUC prevention)
3. Imports HTMX → `window.htmx`
4. Initializes Alpine.js (`Alpine.start()`) → `window.Alpine`
5. Imports chart modules (allocation, evolution, performance, scenario)
6. Auto-initializes charts on `DOMContentLoaded`
7. Re-initializes charts + Alpine tree after HTMX swaps via `htmx:afterSettle` event

### Tailwind v4 Source Scanning
```css
@import "tailwindcss";
@source "../../../templates/**/*.html";
@source "../../../apps/**/templates/**/*.html";
```
Scans all Django templates for class usage — critical for correct CSS purging in production.

### Charts (4 modules)

- **`charts/allocation.js`** — Chart.js doughnut: tree-shaken imports (DoughnutController, ArcElement, Tooltip, Legend). Scans `canvas[data-chart="allocation"]`. Supports custom labels, values, colors via JSON data attribute. Destroys previous instance before re-creating (handles HTMX swaps). 8-color palette. Stores instances in Map for cleanup.

- **`charts/evolution.js`** — Chart.js line with dual Y-axes: principal_series (green filled), interest_series (amber filled), balance_series (indigo dashed, right axis). Custom `currentMonthPlugin` draws red dashed vertical line at current month. Downsampling logic reduces points to max 120 for performance. Auto-steps sampling and maps current month index.

- **`charts/performance.js`** — lightweight-charts (TradingView-style) line chart: scans `[data-chart="performance"]`. Auto-resizes via ResizeObserver. Blue line series with transparent background.

- **`charts/scenario.js`** — Chart.js bar chart: before/after comparison with blue/amber colors. Scans `canvas[data-chart="scenario"]`. Two datasets for comparison.

### Alpine.js Usage Patterns

1. **Toast/Alert auto-dismiss** (base.html): `x-data="{ show: true }"` + `x-init="setTimeout(() => show = false, 5000)"` + `x-transition:leave`
2. **Tooltip popover** (tooltip.html): Dual desktop/mobile mode with `@close-tooltips.window="open = false"` coordination
3. **Toggle switch** (detail.html): `x-data="{ showMine: false }"` for Total/My share view switching
4. **Disclaimer banner** (disclaimer_banner.html): `x-data="{ show: true }"` with `@click="show = false"` + transition
5. **Window-scoped events**: Global `close-tooltips` event pattern for single-tooltip-at-a-time behavior
6. **HTMX + Alpine synergy**: `htmx:afterSettle` listener calls `Alpine.initTree(event.detail.elt)` to reinitialize new DOM

### HTMX Integration Patterns

**Global configuration** (base.html):
- Meta tag: `defaultSwapStyle="innerHTML"`
- Body-level CSRF: `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`

**CRUD pattern** (expenses, taxes, valuations, rate changes, rental income):
```html
<!-- Button loads form -->
hx-get="{% url 'real_estate:add_expense' pk %}" hx-target="#expense-form-container" hx-swap="innerHTML"

<!-- Form submits and replaces list -->
hx-post="{% url 'real_estate:add_expense' pk %}" hx-target="#expense-list" hx-swap="innerHTML"

<!-- Delete with confirmation -->
hx-delete="{% url 'real_estate:delete_expense' pk expense_id %}" hx-confirm="{% trans 'Delete?' %}"
```

**Reactive updates** via HX-Trigger response headers:
```python
response["HX-Trigger"] = "expenses-changed"  # After expense CRUD
response["HX-Trigger"] = "taxes-changed"      # After tax CRUD
response["HX-Trigger"] = "mortgage-changed"    # After rate change
response["HX-Trigger"] = "rental-changed"      # After rental CRUD
response["HX-Trigger"] = "payments-changed"    # After owner payment CRUD
```

**Listener** (monthly cost container):
```html
<div id="monthly-cost-container"
     hx-get="{% url 'real_estate:monthly_cost' property.pk %}"
     hx-trigger="expenses-changed from:body, taxes-changed from:body, rental-changed from:body, mortgage-changed from:body, payments-changed from:body"
     hx-swap="innerHTML">
```

**Sale simulator**: `hx-get` with `hx-trigger="input changed delay:500ms"` + `hx-include` for debounced query

**Form cancellation**: Vanilla JS `onclick="this.closest('form').remove()"`

---

## 8. Internationalization

- **Default language**: French (`LANGUAGE_CODE = "fr"`)
- **Supported**: FR + EN
- **Templates**: `{% trans "..." %}` and `{% blocktrans %}...{% endblocktrans %}`
- **Python**: `gettext_lazy()` for model fields, form labels, service strings, tooltip texts
- **Translation file**: `locale/fr/LC_MESSAGES/django.po` (~2,617 lines, ~614 entries)
- **Coverage**: Province names, risk quiz (6 questions + 25 answers), risk profiles, education UI, asset types, portfolio terms, real estate (property types, mortgage fields, expense types, valuation sources, sale simulation, co-ownership, taxes, charts, notifications, tooltips, rate changes, rental income, monthly costs), navigation, auth, currency labels, **France-specific terms** (département, taxe foncière, taxe d'habitation, IFI, assurance emprunteur, frais de notaire, plus-value, abattements, taux mixte, charges de copropriété)
- **Language switching**: Form POST to Django's `set_language` URL (in sidebar + footer)
- **Curriculum**: Separate directories per language (`Limpid_Crescendo_EN_v1/`, `Limpid_Crescendo_FR_v1/`)

---

## 9. Education Curriculum — "Limpid Crescendo"

18 lessons across 6 levels, ~5-8 minutes each:

| Level | Theme | Lessons |
|-------|-------|---------|
| L0 | Foundations | "What is investing?", "Inflation & purchasing power" |
| L1 | Instruments | "Stocks", "Bonds", "Diversification" |
| L2 | Products | "ETFs", "Funds", "GICs" |
| L3 | Costs | "MERs & fees", "Tax efficiency", "Impact" |
| L4 | Strategy | "Asset allocation", "Rebalancing", "Risk profiles" |
| L5 | Context | "Markets & cycles", "Regulation & protections", "Personal finance framework" |

**Format**: Markdown files with YAML-like frontmatter (title, level, duration_min, tags, key_terms, prerequisites) + JSON quizzes (MCQ with prompt, choices, answer, explanation).

**Pedagogy principles**:
- Contextual (examples use portfolio scenarios)
- Gentle math (percentages, rule of three — no calculus)
- Progress on errors (immediate feedback, never blocking)
- Neutral on facts, rigorous on method (sources always cited)

**Technical implementation**:
- File-based curriculum (not DB-backed) — easy to maintain and translate
- LRU caching (maxsize=64) for lessons and curriculum index
- Lessons loaded as markdown → HTML via `markdown.markdown`
- YAML-like frontmatter parser supports key-value pairs and lists

---

## 10. Real Estate — Deep Dive

The real estate app is the most complex feature, implementing **bi-country** (Canada + France) property management.

### Canadian Financial Specifics
- **Mortgage amortization**: Semi-annual compounding for fixed rates: `monthly_rate = (1 + r/2)^(1/6) - 1`
- **Variable rates**: Simple monthly compounding: `monthly_rate = r / 12`
- **Sale taxes**: Agent commission includes GST/QST at 14.975%
- **Capital gains**: 50% inclusion rate × 45% estimated marginal rate (non-primary residence only)
- **Primary residence exemption**: If `usage == "primary"`, capital_gains_tax = 0
- **Adjusted Cost Base**: Purchase price + welcome tax + notary fees + capital improvements (expenses with `increases_acb=True`)
- **CMHC insurance tiers** (in create.html JS): <5% down (not insurable), 5-10% (4%), 10-15% (3.1%), 15-20% (2.8%), ≥20% (no premium)
- **Tax types**: Municipal tax, School tax
- **Expense types**: renovation, repair, property_tax, insurance, condo_fees, other
- **Default notary fees**: $800

### French Financial Specifics
- **Mortgage amortization**: Simple monthly compounding: `monthly_rate = r / 12` (no semi-annual compounding)
- **Rate types**: Fixed, Variable, **Mixed (taux mixte)** — hybrid rate type common in France
- **Borrower insurance (assurance emprunteur)**: Mandatory, expressed as annual rate (%) on loan principal, added as separate monthly cost on top of mortgage payment. Typical range: 0.15-0.50%
- **Frais de notaire**: 7-8.5% for existing properties, 2-3% for new builds (replaces Canadian "welcome tax" concept)
- **Sale taxes**: Agent commission includes TVA at 20% (vs 14.975% GST/QST in Canada)
- **Capital gains (plus-value immobilière)**: Complex abatement system for non-primary residences:
  - **Income tax (IR)**: 19% with progressive abatement — 6%/year from year 6-20, 4% at year 21, full exemption at 22+
  - **Social contributions (PS)**: 17.2% with separate abatement — 1.65%/year from year 6-21, 1.6% at year 22, 9%/year from year 23-30, full exemption at 30+
  - **Surtax**: Additional 2-6% tax on gains exceeding 50,000 EUR, with smoothing brackets at each tier
- **Primary residence exemption**: Always 0 in both countries
- **Tax types**: Taxe foncière (annual property tax), Taxe d'habitation (abolished 2023 for primary residences), IFI (wealth tax on real estate >1.3M EUR)
- **Expense types**: charges_copro (copropriété fees), assurance_emprunteur (borrower insurance), plus all common types
- **Département system**: Province field holds a département code (01-95, 2A, 2B) with full dropdown of all 96 French départements
- **Default notary fees**: €3,000

### Co-Ownership System
- **Evolving splits**: OwnershipPeriod + OwnershipPeriodShare allow share percentages to change over time. Each period has a start_date and optional end_date (null = ongoing).
- **Invitation workflow**: Creator sends email invitation → pending with token → accept creates ownership + updates current period shares → signal notifies on login
- **Removal workflow**: Admin removes co-owner → current period ends → new period starts with remaining owners equally redistributed
- **Per-owner metrics**: Each owner sees their share of equity, valuation, mortgage, contributions (down payment + principal paid from amortization schedule + expenses)
- **Auto-share calculation**: JS on create form suggests share split based on down payment ratio with hint text
- **Per-owner amortization**: `generate_per_owner_amortization()` splits each payment based on ownership periods and custom OwnerMonthlyPayment overrides

### Multi-Currency Support
- Property stores `currency` field (CAD or EUR, default CAD)
- `show_money` template tag reads `display_currency` from session context processor
- If display differs from native, converts via `exchange_rates.py` (API + cache + fallback)
- Toggle button in detail header: "Convert to EUR" ↔ "Show in CAD"
- 2-state toggle (not 3-state): click once converts, click again reverts to native

### Notification System
- `PropertyNotification` model with 14 verb types
- `notify_co_owners()` broadcasts to all co-owners except actor
- Verbs: invitation_sent, invitation_received, invitation_accepted, co_owner_removed, expense_added/updated/deleted, tax_added/updated/deleted, valuation_added/updated/deleted, property_updated
- Unread badge count in nav via `unread_notifications` context processor (with pulse animation)
- Notification list page + mark-all-read endpoint
- **Login signal**: `user_logged_in` receiver creates notifications for pending invitations matching user's email

### Mortgage Rate Changes
- `MortgageRateChange` model tracks renewals and rate simulations
- `is_simulation` boolean flag distinguishes real renewals from what-if scenarios
- Amortization schedule recalculates payment when encountering a rate change date
- HTMX form loads inline, triggers "mortgage-changed" event on success
- Badge indicator in rate change list for simulations

### Rental Income Tracking
- `RentalIncome` model with monthly_rent, agency_fee_pct, start/end dates
- Net monthly rent = monthly_rent × (1 - agency_fee_pct/100)
- Integrated into monthly cost calculation (offsets costs)
- HTMX CRUD with "rental-changed" trigger

### Monthly Cost Calculation
- Aggregates: mortgage payments + taxes/12 + recurring expenses/12 - rental income
- Supports per-user view (applies ownership share + custom payment splits)
- HTMX partial updates reactively on expenses/taxes/rental/mortgage/payment changes

### HTMX Patterns Used
- **Sale simulator**: `hx-get` with `hx-trigger="input changed delay:500ms"` + `hx-include` for commission field
- **Add expense/tax/valuation/rate-change/rental**: Button `hx-get` loads form into container → form `hx-post` replaces list
- **Edit/delete**: Inline via HTMX, delete uses `hx-delete` with `hx-confirm`
- **Valuation OOB**: After adding valuation, updates current_valuation on property model
- **Amortization auto-scroll**: JS `scrollIntoView({ behavior: 'smooth', block: 'center' })` to current month
- **Reactive event chain**: CRUD triggers → multiple listeners update (monthly cost, charts sidebar)
- **Invitation response**: HTMX accept/decline replaces notification content inline

### Charts on Detail Page
3 doughnut charts using Chart.js allocation pattern:
1. **Equity Breakdown**: equity vs remaining mortgage (green + gray)
2. **Payment Breakdown**: principal paid vs interest paid vs remaining (green + amber + gray)
3. **Expenses by Type**: aggregate by expense_type (auto-colored)

**Evolution Chart** (amortization page):
- Chart.js line with dual Y-axes
- 3 series: principal (green fill), interest (amber fill), balance (indigo dashed)
- Custom plugin draws red dashed line at current month
- Downsampled to max 120 points for performance

### Smart Create Form (Alpine.js + JS in `create.html`)
- **Country toggle**: Dynamically swaps field labels, visibility, and tooltips based on CA/FR selection
- **Date sync**: Purchase date → mortgage start date
- **Principal auto-fill**: purchase_price - total_down_payment
- **CMHC insurance calculation**: Tiered rates by down payment percentage (Canada only)
- **Borrower insurance field**: Shown only for France
- **Département dropdown**: Full 96-département select (France only, replaces province)
- **Co-owner share suggestion**: Based on down payment ratio with hint text
- **Your share display**: 100 - co_owner_share%

### Sale Estimate Partial
- Metric rows: sale price, mortgage balance, gross equity
- Costs section: commission, notary fees, capital gains tax
- **France detail expansion**: When country=FR, shows nested breakdown of holding period, IR tax + abatement, social contributions + abatement, surtax
- Net proceeds: large font, green/red based on positive/negative
- Per-owner breakdown if co-owned

---

## 11. Deployment Architecture

```
User → Cloudflare (HTTPS) → Tunnel → cloudflared → web:8000 (Gunicorn)
                                         ↕
                                     db:5432 (PostgreSQL 16)
```

### Production Stack (deploy/compose.prod.yml)
| Service | Image | Purpose |
|---------|-------|---------|
| db | postgres:16-alpine | Database with pgdata volume, health check (`pg_isready`) |
| web | ghcr.io/vi-ni/limpid:latest | Gunicorn (2 workers, 4 threads, 120s timeout) |
| tunnel | cloudflare/cloudflared:latest | Routes traffic from limpid.viniqo.com |

### Containerfile (Multi-stage)
1. **Stage 1 — Node 22-slim**: Install npm deps, copy `frontend/` + `templates/` + `apps/` (for Tailwind scanning), run `npm run build` → `static/dist/`
2. **Stage 2 — Python 3.12-slim**: Install libpq5, copy uv from astral-sh image, `uv sync --frozen --no-dev --no-editable`, copy built frontend, run `collectstatic` with `SECRET_KEY=build-only`, expose 8000

### CI/CD (.github/workflows/ci.yml)
On push to main:
1. **Lint** (ubuntu-latest): `ruff check .` + `ruff format --check .`
2. **Test** (ubuntu-latest + PostgreSQL 16-alpine service): `pytest --cov=apps --cov-report=term-missing`
3. **Build** (requires lint + test, main branch only): Setup QEMU + Buildx → Build ARM64 image → Push to GHCR with `:latest` + `:git-sha` tags. Lowercase image name via `${IMAGE_NAME,,}`.

Deploy is manual: `ssh rpi "/opt/limpid/deploy.sh"`

### Scripts
- `setup-rpi.sh` — One-time RPi provisioning: install Docker, GHCR login, create /opt/limpid, generate .env (random SECRET_KEY + DB password via `openssl rand`, prompt for tunnel token), start stack, migrate, create superuser, seed data
- `deploy.sh` — Pull latest image, force-recreate web, migrate, show status
- `seed_all.sh` — Run seed_securities + seed_education + seed_impact

### RPi Remote Management
SSH via Cloudflare Tunnel (`ssh rpi` → `ssh.viniqo.com`), secured by Cloudflare Access (email OTP). Tunnel target: `ssh://172.17.0.1:22` (Docker bridge IP, not `host.docker.internal` which doesn't work on Linux).

---

## 12. Completion Status

| Milestone | Status | Details |
|-----------|--------|---------|
| M0 — Scaffold | ✅ Complete | Django + Vite + Docker setup |
| M1 — Accounts & Onboarding | ✅ Complete | 3-step wizard, 6-question quiz, profiles (31 tests) |
| Design System v1 | ✅ Complete | Tailwind v4 theme, 14 components, all pages restyled |
| Design System v2 | ✅ Complete | "Quiet Precision" overhaul: Geist fonts, warm palette, hover animations, staggered entrance |
| Deployment | ✅ Complete | RPi + Cloudflare Tunnel + CI/CD + SSH management |
| M2 — Market Data | ⚠️ Partial | Models + seed data exist; no UI, no live prices |
| M3 — Portfolio Visualization | ⚠️ Partial | Dashboard + charts exist; CSV import not built, no tests |
| M4 — Transparency Dashboard | ❌ Not started | Empty app |
| M5 — Education (Crescendo) | ✅ Complete | 18 lessons (EN+FR) + Django integration, no tests |
| M6 — Scenario Lab | ❌ Scaffolded | Landing page only |
| M7 — Impact Directory | ❌ Scaffolded | Landing page only |
| M8 — Polish & a11y | ⏳ Ongoing | i18n framework in place, ~614 translations |
| Real Estate (Canada) | ✅ Complete | 15 models, co-ownership, Canadian mortgage math, notifications, multi-currency, tooltips, charts, HTMX CRUD, rate changes, rental income, monthly cost, per-owner payments, evolution charts |
| Real Estate (France) | ✅ Complete | Country field, monthly compounding, borrower insurance, département dropdown, French tax types, plus-value with abatements + surtax, TVA on commission, country-aware forms/tooltips/templates |

### Model Count: 23 active models
- accounts: UserProfile, RiskQuizResponse (2)
- portfolio: Portfolio, Holding, Transaction (3)
- market_data: Asset (1)
- education: LessonProgress, QuizResponse, QuizCompletion (3)
- real_estate: Property, PropertyOwnership, OwnershipPeriod, OwnershipPeriodShare, Mortgage, MortgageRateChange, MortgagePayment, OwnerMonthlyPayment, PropertyExpense, PropertyValuation, PropertyTax, RentalIncome, PropertyInvitation, PropertyNotification (14)

### Test Coverage
| App | Tests | Status |
|-----|-------|--------|
| accounts | 31 | Comprehensive (models, views, services) |
| portfolio | 0 | No tests |
| market_data | 0 | No tests |
| education | 0 | No tests |
| real_estate | ~90+ | Comprehensive (models, views, services, filters) — includes Canada + France cases, rate changes, rental income, per-owner amortization |
| **Total** | **~121+** | |

### Migration History (real_estate)
| Migration | Description |
|-----------|-------------|
| 0001_initial | Core models: Property, PropertyOwnership, Mortgage, MortgagePayment, PropertyExpense |
| 0002 | PropertyValuation, PropertyTax |
| 0003 | OwnershipPeriod, OwnershipPeriodShare, PropertyInvitation, PropertyNotification |
| 0004 | (intermediate changes) |
| 0005_add_currency_to_property | Multi-currency support (CAD/EUR) |
| 0006_add_france_support | Country field, borrower_insurance_rate, mixed rate type, French expense types, French tax types |
| 0007 | MortgageRateChange, RentalIncome, OwnerMonthlyPayment, proof_link on expenses |
| 0008 | PropertyInvitation, PropertyNotification refinements |

---

## 13. Key Integration Points

- **Portfolio ↔ Education**: Clarity score checks which asset types the user has learned about (via `ASSET_TYPE_LESSON_MAP` + `LessonProgress`)
- **Portfolio ↔ Accounts**: Sandbox portfolio allocation based on `UserProfile.risk_profile_score`
- **Portfolio ↔ Market Data**: Holdings reference `Asset` model for prices and metadata
- **Dashboard ↔ Education**: "Next lesson" recommendation on dashboard
- **Real Estate → Context Processors**: `unread_notifications` + `currency_context` are globally available
- **Real Estate → Signals**: `user_logged_in` receiver creates notifications for pending invitations
- **All views**: `@login_required` decorator, `gettext_lazy` for i18n
- **Real Estate**: Largely self-contained app (own models, services, templatetags, signals), only cross-app dependency is on auth User model
- **HTMX Event Chain**: Real estate views emit custom events → multiple template containers listen and refresh independently

---

## 14. Key Design Decisions & Rationale

1. **No financial advice** — By design, never recommends products or actions. Educates and shows facts only.
2. **HTMX + Django templates** — Server-side rendering with dynamic partials, avoiding SPA complexity. Vite only for CSS + charts.
3. **Cloudflare Tunnel** — Zero port forwarding, automatic HTTPS, works behind any NAT/firewall. Secured by Cloudflare Access.
4. **CompressedStaticFilesStorage** — Not Manifest variant. Vite already hashes filenames; double-hashing breaks lookups.
5. **Component start/end pattern** — Django template slot-like behavior without custom template tags. Components use `{% include %}` with `with` for props.
6. **Tailwind v4 custom properties** — Enables future palette swaps (dark mode, alternate themes) without touching component code.
7. **Risk quiz is non-blocking** — Users can skip; education is offered, never gatekept.
8. **French-first** — Default language is French, reflecting Quebec target audience.
9. **Markdown lessons** — Content separated from presentation, easy to maintain and translate. YAML frontmatter for metadata.
10. **RPi hosting** — Proves educational tech is viable on minimal infrastructure (~$100 hardware).
11. **FK named `real_estate` not `property`** — Avoids shadowing Python's `@property` decorator which causes `TypeError: 'ForeignKey' object is not callable`.
12. **Custom `|money` filter with manual comma formatting** — Django's `intcomma` uses locale-aware separators (non-breaking space in FR), so a custom implementation with explicit commas ensures consistent `$1,234` output.
13. **Principal paid from schedule, not records** — `MortgagePayment` records are rarely manually created; computing from the amortization schedule gives accurate values automatically.
14. **Tooltip `<span>` elements, not `<div>`** — Tooltips are placed inside stat cards and metric rows. Using `<div>` inside `<p>` or `<h3>` is invalid HTML and breaks Alpine.js initialization. All tooltip inner elements use `<span>` with block display classes.
15. **`x-cloak` for Alpine components** — Prevents flash of tooltip/popover content before Alpine initializes. CSS rule: `[x-cloak] { display: none !important }`.
16. **Global `close-tooltips` event** — Each tooltip `?` button dispatches `close-tooltips` on window before opening, ensuring only one tooltip is visible at a time.
17. **`show_money` simple_tag over filter** — Filters can't access template context. A `simple_tag(takes_context=True)` reads `display_currency` from session to handle multi-currency conversion transparently.
18. **Country-aware strategy dispatch** — Services use `country` parameter to branch mortgage math, sale costs, and capital gains logic rather than inheritance or separate models. Keeps a single Property model with conditional behavior.
19. **Country-aware form and tooltip dicts** — `get_tooltips(country)` merges base + country-specific overrides. Forms dynamically relabel fields in `__init__` based on country. Avoids duplicating forms per country.
20. **Full département dropdown** — All 96 French départements hardcoded in forms.py rather than a separate model, since the list is stable and rarely changes.
21. **Rate change model for mortgage renewals** — Separate `MortgageRateChange` model allows tracking renewals and "what-if" simulations without modifying the original mortgage. Schedule generator adjusts on-the-fly when encountering rate change dates.
22. **Per-owner payment customization** — `OwnerMonthlyPayment` allows deviation from ownership % (e.g., one owner pays 100% of mortgage for a year). Used in `generate_per_owner_amortization` to override default splits.
23. **HTMX event-driven reactivity** — Custom HX-Trigger events (expenses-changed, mortgage-changed, etc.) decouple CRUD actions from dependent UI updates. Multiple containers can independently react to the same event.
24. **Login signal for invitation notifications** — Rather than requiring users to navigate to a specific page, `user_logged_in` signal auto-creates notifications for pending invitations, making them visible immediately.
25. **File-based curriculum, not DB** — Education content in markdown+JSON files enables version control, easy translation, and no DB migrations for content changes. LRU caching prevents repeated file I/O.

---

## 15. Gotchas & Lessons Learned

- **Containerfile — Tailwind scanning**: Templates and `apps/` must be copied into the frontend build stage so `@source` directives scan HTML classes. Without this, Tailwind purges all utility classes.
- **Containerfile — collectstatic**: Needs `SECRET_KEY=build-only` env var at build time since production settings require it.
- **WhiteNoise storage**: Use `CompressedStaticFilesStorage`, NOT `CompressedManifestStaticFilesStorage`.
- **GHCR image name**: Must lowercase `github.repository` for Docker tags (`${IMAGE_NAME,,}`) since `Vi-Ni/limpid` contains uppercase.
- **ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS**: Must match exact Cloudflare domain (`viniqo.com`, not `viniko.com`).
- **Docker Compose v2**: Use `docker compose` (no hyphen) — old `docker-compose` pip package is deprecated.
- **RPi SSH**: Use `ssh rpi` (Cloudflare Tunnel) — WARP blocks local network from IDE terminals. Tunnel target is `ssh://172.17.0.1:22` (Docker bridge IP), not `host.docker.internal` (doesn't work on Linux).
- **Django FK named `property`**: Shadows Python's `@property` decorator. Mortgage model uses `real_estate` instead.
- **`intcomma` locale issue**: Django's `intcomma` uses non-breaking space (`\xa0`) as thousands separator in FR locale. The `|money` filter uses manual comma formatting for consistent output.
- **Block elements in phrasing content**: Placing `<div>` tooltip popovers inside `<p>`, `<dt>`, or `<h3>` tags is invalid HTML. Browsers close the parent tag early, breaking DOM structure and preventing Alpine.js from initializing. Solution: use `<span>` with block display classes, or restructure parents to `<div>`.
- **Alpine.js `@click.stop` prevents `@click.outside`**: When tooltip buttons use `@click.stop`, clicking a different tooltip's button won't trigger `@click.outside` on the first tooltip (event doesn't propagate). Solution: global `close-tooltips` window event dispatched before each open.
- **Multi-currency session toggle**: A 3-state toggle (None→EUR→CAD→None) doesn't work well when the property is CAD — setting display to CAD has no visible effect. Use a 2-state toggle (None↔target) with explicit `?target=` param.
- **Canadian vs French mortgage math**: Canadian mortgages use semi-annual compounding (regulatory standard), while French mortgages use simple monthly compounding. The `monthly_rate` property on Mortgage dispatches based on `self.real_estate.country`, not on rate_type alone.
- **French capital gains abatements**: IR and PS have completely different abatement schedules (22yr vs 30yr for full exemption). These must be computed separately, not as a combined rate.
- **Borrower insurance as rate vs premium**: Canada adds CMHC insurance as a lump sum to principal (`insurance_premium`). France charges it as a monthly rate on the original principal (`borrower_insurance_rate`). Both affect `monthly_payment` but through different mechanisms.
- **Chart downsampling**: Evolution charts with 300+ monthly points cause performance issues. Downsampling to max 120 points with auto-step calculation keeps charts responsive.
- **HTMX + Alpine reinitialization**: After HTMX swaps new DOM content, Alpine components in the swapped content need explicit initialization via `Alpine.initTree(element)` in the `htmx:afterSettle` handler.
- **PostgreSQL for dev**: Dev environment uses PostgreSQL (not SQLite) to match production. Only test settings use in-memory SQLite for speed.

---

## 16. Dependencies

### Runtime (pyproject.toml)
| Package | Version | Purpose |
|---------|---------|---------|
| django | >=5.2,<5.3 | Core framework |
| django-allauth | >=65.0 | Authentication (email login, signup) |
| django-htmx | >=1.21 | HTMX middleware integration |
| django-vite | >=3.0 | Vite manifest integration |
| django-environ | >=0.11 | Environment variable parsing |
| whitenoise | >=6.8 | Static file serving with compression |
| psycopg[binary] | >=3.2 | PostgreSQL adapter |
| gunicorn | >=23.0 | Production WSGI server |
| markdown | >=3.7 | Lesson content rendering |
| python-dateutil | >=2.9 | Date utilities (relativedelta for amortization) |

### Dev
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0 | Testing framework |
| pytest-django | >=4.9 | Django pytest plugin |
| pytest-cov | >=6.0 | Coverage reporting |
| ruff | >=0.8 | Linting & formatting (E, F, I, UP, B, SIM, DJ rules) |
| django-debug-toolbar | >=4.4 | Development toolbar |
| django-browser-reload | >=1.16 | Auto-reload on file changes |
| pre-commit | >=4.0 | Git hooks (ruff check --fix + ruff format) |

### Frontend (package.json)
| Package | Version | Purpose |
|---------|---------|---------|
| vite | ^6.0.0 | Bundler/dev server |
| tailwindcss | ^4.0.0 | Utility CSS framework |
| @tailwindcss/vite | ^4.0.0 | Tailwind v4 Vite plugin |
| htmx.org | ^2.0.0 | HTMX library |
| alpinejs | ^3.14.0 | Reactive components |
| chart.js | ^4.4.0 | Doughnut/bar/line charts |
| lightweight-charts | ^4.2.0 | TradingView-style line charts |

### Ruff Configuration
- Target: Python 3.12
- Line length: 120
- Exclude: `*/migrations/*`
- Rules: E (pycodestyle), F (pyflakes), I (isort), UP (pyupgrade), B (bugbear), SIM (simplify), DJ (Django)
- isort: first-party = ["apps", "config"]

---

## 17. Implementation Plans

### Active Plans (in `docs/plans/`)
- **`plan_miscellaneous_realestate_features.md`** — 8 features being implemented:
  - ✅ Rate change simulation for mortgages
  - ✅ Rental income tracking
  - ✅ Monthly cost calculation
  - ✅ My-share toggle (client-side Alpine state)
  - ✅ Per-owner payment customization
  - ✅ Property deletion with confirmation
  - ✅ Expense proof links (URL field)
  - ✅ Evolution line charts (Chart.js)

### Completed Plans (in `docs/plans/done/`)
1. **`plan_design.md`** — Design overhaul to "Quiet Precision" (Geist fonts, warm stone palette, motion)
2. **`plan_notification.md`** — Notification system (14 verbs, PropertyNotification model, login signal)
3. **`plan_real_estate.md`** — Original real estate architecture (core models, co-ownership, Canadian mortgage)
4. **`plan_real_estate_france.md`** — French support (country field, monthly compounding, plus-value with abatements)
5. **`plan_currency_tooltip.md`** — Multi-currency support (CAD/EUR toggle, exchange API, educational tooltips)
