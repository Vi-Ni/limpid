# Real Estate Form Wizard & Monthly Cost Stat Card

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-page real estate creation form with a guided step-by-step wizard (like the risk quiz), and replace the redundant "Your Share" stat card with a "Monthly Cost" stat card on the detail page.

**Architecture:** The wizard uses a client-side Alpine.js multi-step approach within a single `<form>` tag. Each step shows a focused group of 3-5 fields with educational context explaining what's being asked and why. Navigation between steps is instant (no server round-trip) — the existing `property_create` view handles the final submission unchanged. The stat card swap is a template-only change backed by data already available in the view context.

**Tech Stack:** Django templates, Alpine.js (step state, validation, transitions), HTMX (final submit only), Tailwind CSS v4 (design tokens), existing `property_create` view.

---

## Todo List

### Phase 1: Wizard Shell & Infrastructure
- [x] 1.1 — Rewrite `templates/real_estate/create.html` with Alpine.js `wizardForm()` component, single `<form>` wrapper, progress bar, step containers with `x-show` + slide transitions, and navigation buttons (Back / Next / Create)
- [x] 1.2 — Implement `wizardForm()` JS: step state, `nextStep()` with HTML5 `checkValidity()`, `country` reactive state, dirty flags, all auto-calculation functions (`updatePrincipal`, `updateInsurance`, `updateFraisNotaire`, `updateShareFromDownPayments`), `hasMortgage` tracked state, delegated input listener, `$nextTick` error-jump for server-side validation failures
- [x] 1.3 — Verify shell renders at `/real-estate/create/` without errors
- [x] 1.4 — Commit: wizard shell

### Phase 2: Wizard Step Partials (1-4)
- [x] 2.1 — Create `templates/real_estate/partials/wizard_step_1.html` — Country & property type (3 fields: country with `x-model`, property_type, usage) + educational header explaining country determines tax/mortgage rules
- [x] 2.2 — Verify step 1 renders, country select updates Alpine state
- [x] 2.3 — Commit: step 1
- [x] 2.4 — Create `templates/real_estate/partials/wizard_step_2.html` — Location (5 fields: name, address, city, province/département with `x-show` label toggle, postal_code, currency) + educational header
- [x] 2.5 — Verify step 2 renders, province/département label switches on country change
- [x] 2.6 — Commit: step 2
- [x] 2.7 — Create `templates/real_estate/partials/wizard_step_3.html` — Purchase details (4 fields: purchase_price, purchase_date, welcome_tax/frais de notaire with `x-show` labels, notary_fees/frais d'agence) + educational header explaining equity/tax implications
- [x] 2.8 — Verify step 3 renders with country-dependent labels
- [x] 2.9 — Commit: step 3
- [x] 2.10 — Create `templates/real_estate/partials/wizard_step_4.html` — Current value (3 optional fields: current_valuation, valuation_date, municipal_assessment/valeur cadastrale) + "skip this step" hint box
- [x] 2.11 — Verify these fields are actually optional (no `required` attribute, server accepts empty values). If not, add `required=False` overrides in `PropertyForm.__init__()` ✅ Added `required=False` + model `null=True, blank=True` + migration 0009
- [x] 2.12 — Verify step 4 is skippable (Next works with empty fields)
- [x] 2.13 — Commit: step 4

### Phase 3: Wizard Step Partials (5-7)
- [x] 3.1 — Create `templates/real_estate/partials/wizard_step_5.html` — Ownership (down_payment field + co-owner toggle with `x-model="hasCoOwner"` + conditional co-owner fields: email, down_payment, share % with live "Your share" display via `getYourShare()`)
- [x] 3.2 — Verify co-owner toggle slides in fields, share auto-calculates from down payments
- [x] 3.3 — Commit: step 5
- [x] 3.4 — Create `templates/real_estate/partials/wizard_step_6.html` — Mortgage (10 fields with country-dependent visibility: lender, principal, rate, rate_type, amortization, term_years CA-only, frequency, start_date, insurance CA-only, borrower_rate FR-only) + "skip" hint box
- [x] 3.5 — Wire up auto-fill triggers: delegated input listener in `init()` for purchase_price/down_payment/co_owner_down_payment → `updateAll()`, dirty flag tracking, purchase_date → mortgage start_date sync
- [x] 3.6 — Verify mortgage step: principal auto-fills from price minus down payments, CMHC insurance auto-calcs for CA, `hasMortgage` updates
- [x] 3.7 — Commit: step 6
- [x] 3.8 — Create `templates/real_estate/partials/wizard_step_7.html` — Review & submit: summary sections (Property, Location, Purchase, Mortgage if `hasMortgage`, Co-ownership if `hasCoOwner`) each with "Edit" button (`@click="step = N"`) and live `x-text` DOM reads for values
- [x] 3.9 — Verify review step shows entered data, "Edit" buttons jump to correct steps, "Create property" submits the form
- [x] 3.10 — Commit: step 7

### Phase 4: Wizard Testing
- [x] 4.1 — Add `PropertyCreateWizardTest` to `apps/real_estate/tests/test_views.py`: test create page renders wizard shell (`wizardForm`, `data-step` in response)
- [x] 4.2 — Add test: form POST with all required fields still works (same data format, 302 redirect on success) + test without valuation fields (302 redirect, None values)
- [x] 4.3 — Run wizard tests: `uv run pytest apps/real_estate/tests/test_views.py -v -k "wizard"` ✅ 3 passed
- [x] 4.4 — Run full real_estate test suite: `uv run pytest apps/real_estate/tests/ -v` ✅ 213 passed → 217 passed
- [x] 4.5 — Commit: wizard tests

### Phase 5: Monthly Cost Stat Card
- [x] 5.1 — In `templates/real_estate/detail.html`, remove the 4th stat card ("Your share": `owner_snapshot.your_equity` with `share_pct` annotation)
- [x] 5.2 — Replace with "Monthly cost" stat card: Total mode (`x-show="!showMine"`) shows `cost_total.total_monthly`, My Share mode (`{% if has_co_owners %}`, `x-show="showMine"`) shows `cost_mine.your_total_monthly` with `owner_pct` annotation
- [x] 5.3 — Add `{% with owner_pct=owner_snapshot.share_pct|floatformat:0|add:"%" %}` wrapping the stat cards grid, close `{% endwith %}` after grid
- [x] 5.4 — Modify Card 1 My Share annotation: change from `snapshot.appreciation_pct|signed_pct` to `owner_pct` (ownership %) — so Value card shows ownership % in My Share mode instead of appreciation
- [x] 5.5 — Verify 4 stat cards display correctly: Value, Equity, Mortgage, Monthly Cost
- [x] 5.6 — Verify toggle: My Share mode shows user-specific values, Value card shows ownership %, Monthly Cost shows user's cost
- [x] 5.7 — Commit: stat card replacement

### Phase 6: Stat Card Testing & Verification
- [x] 6.1 — Verify `monthly_cost` tooltip key exists in `apps/real_estate/tooltips.py` ✅ Exists at line 85-88
- [x] 6.2 — Verify HTMX monthly cost breakdown card (below stat cards) still updates on expense/tax/rental changes
- [x] 6.3 — Add `TestMonthlyCostStatCard` test class checking `monthly_cost` in response content
- [x] 6.4 — Run tests: `uv run pytest apps/real_estate/tests/test_views.py -v` ✅ All pass
- [x] 6.5 — Commit: stat card tests

### Phase 7: Translations & Final Integration
- [x] 7.1 — Run `uv run python manage.py makemessages -l fr --no-wrap` to extract new strings
- [x] 7.2 — Translate all new wizard strings in `locale/fr/LC_MESSAGES/django.po` (~30 new entries translated)
- [x] 7.3 — Compile: `uv run python manage.py compilemessages` ✅
- [x] 7.4 — Commit: translations
- [x] 7.5 — Manual test: create CA property via wizard (7 steps, auto-calculations, submit, verify detail page stat cards)
- [x] 7.6 — Manual test: create FR property with co-owner via wizard (département dropdown, frais de notaire auto-fill, borrower insurance, co-owner invitation, toggle on detail page)
- [x] 7.7 — Manual test: back navigation preserves data, validation blocks on required empty fields, server-side errors jump to correct step
- [x] 7.8 — Run full test suite: `uv run pytest -v` ✅ 249 passed + lint clean
- [x] 7.9 — Final commit if any cleanup needed

---

## Why This Plan

### Problem 1: Create form is overwhelming
The current create form dumps ~30 fields across 3 sections on a single page. For a beginner user (Limpid's target), this is intimidating — they don't know what "welcome tax" or "amortization years" means, and seeing everything at once causes cognitive overload.

### Problem 2: "Your Share" stat card duplicates info
When the "My Share" toggle is ON, card 2 shows "Your equity: $X" and card 4 shows "Your share: $X (50%)". The dollar value is identical. The user sees the same number twice. Meanwhile, the most actionable metric — monthly cost — is buried further down the page in a card, not visible at a glance.

### Solution 1: Step-by-step wizard
Break the form into 7 logical steps (3-5 fields each), each with a short explanation of what we're asking and why it matters. Same pattern as the risk quiz: progress bar, focused content, clear "Next" button. Client-side only (Alpine.js) — no new views needed.

### Solution 2: Monthly cost stat card
Replace card 4 with monthly cost. Total mode shows total monthly cost, My Share mode shows user's monthly cost. Ownership percentage moves to an annotation on the Value card (My Share mode).

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `templates/real_estate/create.html` | **Rewrite** | New wizard template with Alpine.js multi-step |
| `templates/real_estate/partials/wizard_step_1.html` | **Create** | Step 1: Country & property type |
| `templates/real_estate/partials/wizard_step_2.html` | **Create** | Step 2: Location |
| `templates/real_estate/partials/wizard_step_3.html` | **Create** | Step 3: Purchase details |
| `templates/real_estate/partials/wizard_step_4.html` | **Create** | Step 4: Current value |
| `templates/real_estate/partials/wizard_step_5.html` | **Create** | Step 5: Ownership |
| `templates/real_estate/partials/wizard_step_6.html` | **Create** | Step 6: Mortgage |
| `templates/real_estate/partials/wizard_step_7.html` | **Create** | Step 7: Review & submit |
| `templates/real_estate/detail.html` | **Modify** | Replace card 4, adjust annotations |
| `templates/real_estate/partials/monthly_cost.html` | **Modify** | Remove duplicate monthly cost from below (optional) |
| `apps/real_estate/views.py` | **No change** | `property_create` view works as-is |
| `apps/real_estate/forms.py` | **No change** | Forms work as-is |
| `apps/real_estate/tests/test_views.py` | **Modify** | Add wizard-specific tests |
| `locale/fr/LC_MESSAGES/django.po` | **Modify** | New translatable strings |

**Key constraint:** The `property_create` view and forms are NOT modified. The wizard is purely a template-level reorganization of the same form fields. The `<form>` tag wraps all 7 steps and submits once at the end.

---

## Chunk 1: Wizard Form

### Task 1: Create the wizard shell template

**Files:**
- Rewrite: `templates/real_estate/create.html`

This is the outer wrapper: the `<form>` tag, Alpine.js state, progress bar, and step container. All step partials are `{% include %}`'d inside and shown/hidden via `x-show`.

- [ ] **Step 1: Write the new create.html shell**

Replace `templates/real_estate/create.html` entirely. The shell provides:
- A single `<form method="post">` wrapping all steps (same action as current)
- Alpine.js component `x-data="wizardForm()"` managing: `step` (1-7), `totalSteps` (7), `country` (synced from select), validation helpers
- Progress bar component (reuse `components/progress_bar.html` pattern)
- Step container with transition animations
- Navigation buttons (Back / Next / Create) that change per step
- All existing JS auto-calculation logic (CMHC, principal, notary fees, share) preserved

```html
{% extends "base.html" %}
{% load i18n django_vite real_estate_filters %}

{% block content %}
<div class="container-limpid max-w-2xl py-8" x-data="wizardForm()" x-cloak>

  {# ── Progress bar ── #}
  <div class="mb-8">
    <div class="flex items-center justify-between mb-2">
      <p class="text-sm text-text-muted">
        {% blocktranslate with current='<span x-text="step"></span>' total='<span x-text="totalSteps"></span>' %}Step {{ current }} of {{ total }}{% endblocktranslate %}
      </p>
      <button type="button"
              x-show="step > 1"
              @click="step--"
              class="text-sm text-primary-600 hover:text-primary-700 font-medium">
        ← {% trans "Back" %}
      </button>
    </div>
    <div class="h-1.5 w-full overflow-hidden rounded-full bg-bg-subtle">
      <div class="h-full rounded-full bg-primary-500 transition-all duration-500 ease-out"
           :style="'width: ' + (step / totalSteps * 100) + '%'">
      </div>
    </div>
  </div>

  {# ── Form wraps ALL steps ── #}
  <form method="post" id="wizard-form">
    {% csrf_token %}

    {# Steps are included here, each wrapped in x-show #}
    <div x-show="step === 1" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_1.html" %}
    </div>

    <div x-show="step === 2" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_2.html" %}
    </div>

    <div x-show="step === 3" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_3.html" %}
    </div>

    <div x-show="step === 4" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_4.html" %}
    </div>

    <div x-show="step === 5" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_5.html" %}
    </div>

    <div x-show="step === 6" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_6.html" %}
    </div>

    <div x-show="step === 7" x-transition:enter="transition ease-out duration-200"
         x-transition:enter-start="opacity-0 translate-x-4"
         x-transition:enter-end="opacity-100 translate-x-0">
      {% include "real_estate/partials/wizard_step_7.html" %}
    </div>

    {# ── Navigation buttons ── #}
    <div class="mt-8 flex items-center gap-3">
      <template x-if="step < totalSteps">
        <button type="button" @click="nextStep()" class="btn-primary w-full">
          {% trans "Next" %} →
        </button>
      </template>
      <template x-if="step === totalSteps">
        <button type="submit" class="btn-primary w-full">
          {% trans "Create property" %}
        </button>
      </template>
    </div>

    <div class="mt-3 text-center">
      <a href="{% url 'real_estate:list' %}" class="text-sm text-text-muted hover:text-text">
        {% trans "Cancel" %}
      </a>
    </div>
  </form>
</div>

<script>
function wizardForm() {
  return {
    step: 1,
    totalSteps: 7,

    // ── Reactive state ──
    country: '{{ form.country.value|default:"CA" }}',
    hasCoOwner: false,

    // ── Dirty flags (prevent auto-overwrite of user edits) ──
    _principalDirty: false,
    _insuranceDirty: false,
    _shareDirty: false,
    _welcomeTaxDirty: false,
    _currencyDirty: false,
    _provinceDirty: false,

    init() {
      // Watch country changes
      this.$watch('country', () => this.onCountryChange());

      // ── Jump to first step with errors on server-side validation failure ──
      // Django re-renders the form with error classes. Detect and jump.
      this.$nextTick(() => {
        const errorEl = this.$el.querySelector('.text-danger-600');
        if (errorEl) {
          const stepEl = errorEl.closest('[data-step]');
          if (stepEl) this.step = parseInt(stepEl.dataset.step);
        }
      });
    },

    // ── Step validation ──
    // Uses HTML5 constraint validation API on visible required fields
    nextStep() {
      const stepEl = this.$el.querySelector(`[data-step="${this.step}"]`);
      if (stepEl) {
        const inputs = stepEl.querySelectorAll('input, select, textarea');
        let valid = true;
        inputs.forEach(el => {
          if (!el.checkValidity()) {
            el.classList.add('input-error');
            el.reportValidity();
            valid = false;
          } else {
            el.classList.remove('input-error');
          }
        });
        if (!valid) return;
      }
      if (this.step < this.totalSteps) this.step++;
    },

    // ── Country change logic (from current create.html) ──
    onCountryChange() {
      const currencyEl = document.getElementById('id_currency');
      const provinceEl = document.getElementById('id_province');
      if (currencyEl && !this._currencyDirty) {
        currencyEl.value = this.country === 'FR' ? 'EUR' : 'CAD';
      }
      if (provinceEl && !this._provinceDirty) {
        provinceEl.value = this.country === 'FR' ? '' : 'QC';
      }
      this.updateAll();
    },

    // ── Auto-calculations (preserved from current JS) ──
    updateAll() {
      this.updatePrincipal();
      this.updateInsurance();
      this.updateFraisNotaire();
      this.updateShareFromDownPayments();
    },

    updatePrincipal() {
      if (this._principalDirty) return;
      const price = parseFloat(document.getElementById('id_purchase_price')?.value) || 0;
      const down = parseFloat(document.getElementById('id_down_payment')?.value) || 0;
      const coDown = parseFloat(document.getElementById('id_co_owner_down_payment')?.value) || 0;
      const principalEl = document.getElementById('id_mortgage-principal');
      if (principalEl && price > 0) {
        const val = Math.max(0, price - down - coDown).toFixed(2);
        principalEl.value = val;
        this.hasMortgage = parseFloat(val) > 0;
      }
    },

    updateInsurance() {
      if (this._insuranceDirty || this.country !== 'CA') return;
      const price = parseFloat(document.getElementById('id_purchase_price')?.value) || 0;
      const down = parseFloat(document.getElementById('id_down_payment')?.value) || 0;
      const coDown = parseFloat(document.getElementById('id_co_owner_down_payment')?.value) || 0;
      const totalDown = down + coDown;
      const el = document.getElementById('id_mortgage-insurance_premium');
      if (!el || price <= 0) return;
      const ratio = totalDown / price;
      let rate = 0;
      if (ratio < 0.05) rate = 0;
      else if (ratio < 0.10) rate = 0.04;
      else if (ratio < 0.15) rate = 0.031;
      else if (ratio < 0.20) rate = 0.028;
      el.value = ((price - totalDown) * rate).toFixed(2);
    },

    updateFraisNotaire() {
      if (this._welcomeTaxDirty || this.country !== 'FR') return;
      const price = parseFloat(document.getElementById('id_purchase_price')?.value) || 0;
      const el = document.getElementById('id_welcome_tax_paid');
      if (el && price > 0) el.value = (price * 0.08).toFixed(2);
    },

    updateShareFromDownPayments() {
      if (this._shareDirty) return;
      const down = parseFloat(document.getElementById('id_down_payment')?.value) || 0;
      const coDown = parseFloat(document.getElementById('id_co_owner_down_payment')?.value) || 0;
      const total = down + coDown;
      const el = document.getElementById('id_co_owner_share');
      if (el && total > 0 && coDown > 0) {
        el.value = ((coDown / total) * 100).toFixed(2);
      }
    },

    // ── Tracked state for review step reactivity ──
    hasMortgage: false,

    getYourShare() {
      const coShare = parseFloat(document.getElementById('id_co_owner_share')?.value) || 0;
      if (coShare >= 1 && coShare <= 99) return (100 - coShare).toFixed(2) + '%';
      return '—';
    },
  };
}
</script>
{% endblock %}
```

- [ ] **Step 2: Verify the shell renders without errors**

Run the dev server and navigate to `/real-estate/create/`. The page should load with the progress bar and empty step containers. The form should submit to the same URL as before.

```bash
uv run python manage.py runserver
# Visit http://localhost:8000/real-estate/create/
```

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/create.html
git commit -m "refactor: replace single-page create form with wizard shell"
```

---

### Task 2: Step 1 — Country & property type

**Files:**
- Create: `templates/real_estate/partials/wizard_step_1.html`

This is the first thing users see. Three simple dropdowns with educational context: "Let's start with the basics about your property."

- [ ] **Step 1: Create the step 1 partial**

```html
{% load i18n %}

<div data-step="1">
  {# ── Educational header ── #}
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "What kind of property?" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "Start by telling us the basics. The country determines tax rules, mortgage calculations, and which fields we'll ask about." %}
    </p>
  </div>

  {# ── Fields ── #}
  <div class="space-y-5">
    {# Country — rendered manually (not {{ form.country }}) to attach x-model for Alpine.js reactivity #}
    <div>
      <label for="id_country" class="block text-sm font-medium text-text mb-1">
        {{ form.country.label }}
      </label>
      <select name="country" id="id_country"
              class="input w-full" required
              x-model="country">
        {% for value, label in form.country.field.choices %}
        <option value="{{ value }}" {% if value == form.country.value %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
      </select>
      {% if form.country.help_text %}
      <p class="mt-1 text-xs text-text-faint">{{ form.country.help_text }}</p>
      {% endif %}
      {% if form.country.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.country.errors.0 }}</p>
      {% endif %}
    </div>

    {# Property type #}
    <div>
      <label for="id_property_type" class="block text-sm font-medium text-text mb-1">
        {{ form.property_type.label }}
      </label>
      {{ form.property_type }}
      {% if form.property_type.help_text %}
      <p class="mt-1 text-xs text-text-faint">{{ form.property_type.help_text }}</p>
      {% endif %}
      {% if form.property_type.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.property_type.errors.0 }}</p>
      {% endif %}
    </div>

    {# Usage #}
    <div>
      <label for="id_usage" class="block text-sm font-medium text-text mb-1">
        {{ form.usage.label }}
      </label>
      {{ form.usage }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "Primary residences are exempt from capital gains tax when sold." %}
      </p>
      {% if form.usage.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.usage.errors.0 }}</p>
      {% endif %}
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verify step 1 renders**

Navigate to `/real-estate/create/`. Step 1 should display the country, property type, and usage fields with the educational header. Changing country should update the Alpine `country` variable.

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/wizard_step_1.html
git commit -m "feat: add wizard step 1 — country & property type"
```

---

### Task 3: Step 2 — Location

**Files:**
- Create: `templates/real_estate/partials/wizard_step_2.html`

Location fields with country-dependent province/département.

- [ ] **Step 1: Create the step 2 partial**

```html
{% load i18n %}

<div data-step="2">
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "Where is it located?" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "The address helps track your property and determines local tax rules." %}
    </p>
  </div>

  <div class="space-y-5">
    {# Name #}
    <div>
      <label for="id_name" class="block text-sm font-medium text-text mb-1">
        {{ form.name.label }}
      </label>
      {{ form.name }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "A friendly name to identify this property (e.g. \"Our first home\")." %}
      </p>
      {% if form.name.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.name.errors.0 }}</p>
      {% endif %}
    </div>

    {# Address #}
    <div>
      <label for="id_address" class="block text-sm font-medium text-text mb-1">
        {{ form.address.label }}
      </label>
      {{ form.address }}
      {% if form.address.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.address.errors.0 }}</p>
      {% endif %}
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# City #}
      <div>
        <label for="id_city" class="block text-sm font-medium text-text mb-1">
          {{ form.city.label }}
        </label>
        {{ form.city }}
        {% if form.city.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.city.errors.0 }}</p>
        {% endif %}
      </div>

      {# Province / Département (country-dependent) #}
      <div>
        <label for="id_province" class="block text-sm font-medium text-text mb-1">
          <span x-show="country !== 'FR'">{% trans "Province" %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Département" %}</span>
        </label>
        {{ form.province }}
        {% if form.province.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.province.errors.0 }}</p>
        {% endif %}
      </div>
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Postal code #}
      <div>
        <label for="id_postal_code" class="block text-sm font-medium text-text mb-1">
          {{ form.postal_code.label }}
        </label>
        {{ form.postal_code }}
        {% if form.postal_code.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.postal_code.errors.0 }}</p>
        {% endif %}
      </div>

      {# Currency (auto-filled by country, but editable) #}
      <div>
        <label for="id_currency" class="block text-sm font-medium text-text mb-1">
          {{ form.currency.label }}
        </label>
        {{ form.currency }}
        {% if form.currency.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.currency.errors.0 }}</p>
        {% endif %}
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verify step 2 renders and country toggle works**

Navigate to `/real-estate/create/`, click "Next" on step 1. Step 2 should show location fields. Province/Département label should switch when you go back to step 1 and change country.

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/wizard_step_2.html
git commit -m "feat: add wizard step 2 — location"
```

---

### Task 4: Step 3 — Purchase details

**Files:**
- Create: `templates/real_estate/partials/wizard_step_3.html`

Financial purchase details with country-dependent labels and auto-calculation hints.

- [ ] **Step 1: Create the step 3 partial**

```html
{% load i18n %}

<div data-step="3">
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "Purchase details" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "These details help calculate your equity, tax obligations, and cost of ownership over time." %}
    </p>
  </div>

  <div class="space-y-5">
    {# Purchase price #}
    <div>
      <label for="id_purchase_price" class="block text-sm font-medium text-text mb-1">
        {{ form.purchase_price.label }}
      </label>
      {{ form.purchase_price }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "The total price you paid (or agreed to pay) for the property." %}
      </p>
      {% if form.purchase_price.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.purchase_price.errors.0 }}</p>
      {% endif %}
    </div>

    {# Purchase date #}
    <div>
      <label for="id_purchase_date" class="block text-sm font-medium text-text mb-1">
        {{ form.purchase_date.label }}
      </label>
      {{ form.purchase_date }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "Used to calculate holding period for capital gains tax." %}
      </p>
      {% if form.purchase_date.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.purchase_date.errors.0 }}</p>
      {% endif %}
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Welcome tax / Frais de notaire #}
      <div>
        <label for="id_welcome_tax_paid" class="block text-sm font-medium text-text mb-1">
          <span x-show="country !== 'FR'">{% trans "Welcome tax paid" %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Frais de notaire (achat)" %}</span>
        </label>
        {{ form.welcome_tax_paid }}
        <p class="mt-1 text-xs text-text-faint">
          <span x-show="country !== 'FR'">{% trans "One-time municipal tax on property transfer." %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Typically 7-8% of the purchase price for existing properties." %}</span>
        </p>
        {% if form.welcome_tax_paid.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.welcome_tax_paid.errors.0 }}</p>
        {% endif %}
      </div>

      {# Notary fees / Frais d'agence #}
      <div>
        <label for="id_notary_fees_purchase" class="block text-sm font-medium text-text mb-1">
          <span x-show="country !== 'FR'">{% trans "Notary fees at purchase" %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Frais d'agence (achat)" %}</span>
        </label>
        {{ form.notary_fees_purchase }}
        {% if form.notary_fees_purchase.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.notary_fees_purchase.errors.0 }}</p>
        {% endif %}
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verify step 3 renders**

Navigate through steps 1-2, then to step 3. Purchase fields should render with country-dependent labels. Entering a purchase price on step 3 should eventually auto-fill the mortgage principal on step 6 (tested later).

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/wizard_step_3.html
git commit -m "feat: add wizard step 3 — purchase details"
```

---

### Task 5: Step 4 — Current value (optional)

**Files:**
- Create: `templates/real_estate/partials/wizard_step_4.html`

Optional valuation fields. The educational text should make clear these are optional but useful for tracking appreciation.

- [ ] **Step 1: Create the step 4 partial**

```html
{% load i18n %}

<div data-step="4">
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "What's it worth today?" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "These fields are optional. If you know the current value, it helps us show your equity and appreciation over time." %}
    </p>
  </div>

  {# ── Optional hint ── #}
  <div class="mb-5 rounded-xl bg-bg-subtle px-4 py-3 text-sm text-text-muted">
    {% trans "You can skip this step and add valuations later from the property detail page." %}
  </div>

  <div class="space-y-5">
    {# Current valuation #}
    <div>
      <label for="id_current_valuation" class="block text-sm font-medium text-text mb-1">
        {{ form.current_valuation.label }}
      </label>
      {{ form.current_valuation }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "Your best estimate of the property's current market value." %}
      </p>
      {% if form.current_valuation.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.current_valuation.errors.0 }}</p>
      {% endif %}
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Valuation date #}
      <div>
        <label for="id_valuation_date" class="block text-sm font-medium text-text mb-1">
          {{ form.valuation_date.label }}
        </label>
        {{ form.valuation_date }}
        {% if form.valuation_date.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.valuation_date.errors.0 }}</p>
        {% endif %}
      </div>

      {# Municipal assessment #}
      <div>
        <label for="id_municipal_assessment" class="block text-sm font-medium text-text mb-1">
          <span x-show="country !== 'FR'">{% trans "Municipal assessment" %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Valeur cadastrale" %}</span>
        </label>
        {{ form.municipal_assessment }}
        <p class="mt-1 text-xs text-text-faint">
          <span x-show="country !== 'FR'">{% trans "From your municipal tax bill." %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Valeur cadastrale de la taxe foncière." %}</span>
        </p>
        {% if form.municipal_assessment.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ form.municipal_assessment.errors.0 }}</p>
        {% endif %}
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verify step 4 fields are actually optional**

The `current_valuation`, `valuation_date`, and `municipal_assessment` fields must be optional for this step to be skippable. Verify by checking the existing create form works without these fields. If `nextStep()` blocks on empty fields or server validation rejects, add `required=False` overrides in `PropertyForm.__init__()`:

```python
for field_name in ("current_valuation", "valuation_date", "municipal_assessment"):
    if field_name in self.fields:
        self.fields[field_name].required = False
```

- [ ] **Step 3: Verify step 4 renders and is skippable**

Navigate through steps 1-3, then to step 4. All fields should be optional. Clicking "Next" with empty fields should work.

- [ ] **Step 4: Commit**

```bash
git add templates/real_estate/partials/wizard_step_4.html
git commit -m "feat: add wizard step 4 — current value (optional)"
```

---

### Task 6: Step 5 — Ownership

**Files:**
- Create: `templates/real_estate/partials/wizard_step_5.html`

Down payment and optional co-owner section. The co-owner toggle uses Alpine.js `hasCoOwner`.

- [ ] **Step 1: Create the step 5 partial**

```html
{% load i18n %}

<div data-step="5">
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "Who owns this property?" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "Your down payment is used to calculate the initial mortgage amount and your ownership share if you have a co-owner." %}
    </p>
  </div>

  <div class="space-y-5">
    {# Your down payment #}
    <div>
      <label for="id_down_payment" class="block text-sm font-medium text-text mb-1">
        {% trans "Your down payment" %}
      </label>
      {{ form.down_payment }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "The amount you put down at purchase. This reduces the mortgage principal." %}
      </p>
      {% if form.down_payment.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ form.down_payment.errors.0 }}</p>
      {% endif %}
    </div>

    {# Co-owner toggle #}
    <div class="rounded-xl border border-border p-4">
      <label class="flex cursor-pointer items-center gap-3">
        <div class="relative">
          <input type="checkbox" class="sr-only peer" x-model="hasCoOwner">
          <div class="h-5 w-9 rounded-full bg-border peer-checked:bg-primary-600 transition"></div>
          <div class="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition peer-checked:translate-x-4"></div>
        </div>
        <span class="text-sm font-medium text-text">{% trans "I have a co-owner" %}</span>
      </label>

      {# Co-owner fields (conditional) #}
      <div x-show="hasCoOwner" x-cloak x-transition class="mt-5 space-y-5 border-t border-border pt-5">
        <p class="text-sm text-text-muted">
          {% trans "We'll send them an invitation. They can accept and see the property from their own account." %}
        </p>

        {# Co-owner email #}
        <div>
          <label for="id_co_owner_email" class="block text-sm font-medium text-text mb-1">
            {% trans "Co-owner email" %}
          </label>
          {{ form.co_owner_email }}
          {% if form.co_owner_email.errors %}
          <p class="mt-1 text-xs text-danger-600">{{ form.co_owner_email.errors.0 }}</p>
          {% endif %}
        </div>

        {# Co-owner down payment #}
        <div>
          <label for="id_co_owner_down_payment" class="block text-sm font-medium text-text mb-1">
            {% trans "Co-owner down payment" %}
          </label>
          {{ form.co_owner_down_payment }}
          {% if form.co_owner_down_payment.errors %}
          <p class="mt-1 text-xs text-danger-600">{{ form.co_owner_down_payment.errors.0 }}</p>
          {% endif %}
        </div>

        {# Ownership share #}
        <div>
          <label for="id_co_owner_share" class="block text-sm font-medium text-text mb-1">
            {% trans "Co-owner share (%)" %}
          </label>
          {{ form.co_owner_share }}
          <p class="mt-1 text-xs text-text-faint">
            {% trans "Percentage of ownership for the co-owner (1-99%). Your share:" %}
            <span class="font-medium text-text" x-text="getYourShare()"></span>
          </p>
          {% if form.co_owner_share.errors %}
          <p class="mt-1 text-xs text-danger-600">{{ form.co_owner_share.errors.0 }}</p>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Verify co-owner toggle and share calculation**

Navigate to step 5. Toggle "I have a co-owner" — fields should slide in. Enter down payments for both owners — co-owner share should auto-calculate. "Your share" display should update reactively.

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/wizard_step_5.html
git commit -m "feat: add wizard step 5 — ownership"
```

---

### Task 7: Step 6 — Mortgage (optional)

**Files:**
- Create: `templates/real_estate/partials/wizard_step_6.html`

All mortgage fields with country-dependent visibility. Optional step — users can skip if they own outright.

- [ ] **Step 1: Create the step 6 partial**

```html
{% load i18n %}

<div data-step="6">
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "How is it financed?" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "If you have a mortgage, fill in the details below. This lets us generate your full amortization schedule and track equity over time." %}
    </p>
  </div>

  {# ── Optional hint ── #}
  <div class="mb-5 rounded-xl bg-bg-subtle px-4 py-3 text-sm text-text-muted">
    {% trans "No mortgage? Skip this step — you can always add one later." %}
  </div>

  <div class="space-y-5">
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Lender #}
      <div>
        <label for="id_mortgage-lender" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.lender.label }}
        </label>
        {{ mortgage_form.lender }}
        {% if mortgage_form.lender.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.lender.errors.0 }}</p>
        {% endif %}
      </div>

      {# Principal #}
      <div>
        <label for="id_mortgage-principal" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.principal.label }}
        </label>
        {{ mortgage_form.principal }}
        <p class="mt-1 text-xs text-text-faint">
          {% trans "Auto-calculated from purchase price minus down payments." %}
        </p>
        {% if mortgage_form.principal.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.principal.errors.0 }}</p>
        {% endif %}
      </div>
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Annual rate #}
      <div>
        <label for="id_mortgage-annual_rate" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.annual_rate.label }}
        </label>
        {{ mortgage_form.annual_rate }}
        <p class="mt-1 text-xs text-text-faint">
          <span x-show="country !== 'FR'">{% trans "Canadian fixed rates use semi-annual compounding." %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "French rates use simple monthly compounding." %}</span>
        </p>
        {% if mortgage_form.annual_rate.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.annual_rate.errors.0 }}</p>
        {% endif %}
      </div>

      {# Rate type #}
      <div>
        <label for="id_mortgage-rate_type" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.rate_type.label }}
        </label>
        {{ mortgage_form.rate_type }}
        {% if mortgage_form.rate_type.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.rate_type.errors.0 }}</p>
        {% endif %}
      </div>
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Amortization years #}
      <div>
        <label for="id_mortgage-amortization_years" class="block text-sm font-medium text-text mb-1">
          <span x-show="country !== 'FR'">{% trans "Amortization (years)" %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Loan duration (years)" %}</span>
        </label>
        {{ mortgage_form.amortization_years }}
        <p class="mt-1 text-xs text-text-faint">
          <span x-show="country !== 'FR'">{% trans "Typically 25 years in Canada." %}</span>
          <span x-show="country === 'FR'" x-cloak>{% trans "Typically 20-25 years in France." %}</span>
        </p>
        {% if mortgage_form.amortization_years.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.amortization_years.errors.0 }}</p>
        {% endif %}
      </div>

      {# Term years — CA only #}
      <div x-show="country !== 'FR'" x-cloak>
        <label for="id_mortgage-term_years" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.term_years.label }}
        </label>
        {{ mortgage_form.term_years }}
        <p class="mt-1 text-xs text-text-faint">
          {% trans "Typically 5 years. You'll renew at a new rate when the term ends." %}
        </p>
        {% if mortgage_form.term_years.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.term_years.errors.0 }}</p>
        {% endif %}
      </div>
    </div>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {# Payment frequency #}
      <div>
        <label for="id_mortgage-payment_frequency" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.payment_frequency.label }}
        </label>
        {{ mortgage_form.payment_frequency }}
        {% if mortgage_form.payment_frequency.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.payment_frequency.errors.0 }}</p>
        {% endif %}
      </div>

      {# Start date #}
      <div>
        <label for="id_mortgage-start_date" class="block text-sm font-medium text-text mb-1">
          {{ mortgage_form.start_date.label }}
        </label>
        {{ mortgage_form.start_date }}
        <p class="mt-1 text-xs text-text-faint">
          {% trans "Usually the same as your purchase date." %}
        </p>
        {% if mortgage_form.start_date.errors %}
        <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.start_date.errors.0 }}</p>
        {% endif %}
      </div>
    </div>

    {# Insurance premium — CA only #}
    <div x-show="country !== 'FR'" x-cloak>
      <label for="id_mortgage-insurance_premium" class="block text-sm font-medium text-text mb-1">
        {{ mortgage_form.insurance_premium.label }}
      </label>
      {{ mortgage_form.insurance_premium }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "CMHC/Sagen/Canada Guaranty insurance. Required if down payment is less than 20%. Auto-calculated." %}
      </p>
      {% if mortgage_form.insurance_premium.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.insurance_premium.errors.0 }}</p>
      {% endif %}
    </div>

    {# Borrower insurance rate — FR only #}
    <div x-show="country === 'FR'" x-cloak>
      <label for="id_mortgage-borrower_insurance_rate" class="block text-sm font-medium text-text mb-1">
        {{ mortgage_form.borrower_insurance_rate.label }}
      </label>
      {{ mortgage_form.borrower_insurance_rate }}
      <p class="mt-1 text-xs text-text-faint">
        {% trans "Annual rate (%) for assurance emprunteur. Typically 0.15-0.50%. Added monthly on top of your mortgage payment." %}
      </p>
      {% if mortgage_form.borrower_insurance_rate.errors %}
      <p class="mt-1 text-xs text-danger-600">{{ mortgage_form.borrower_insurance_rate.errors.0 }}</p>
      {% endif %}
    </div>
  </div>
</div>
```

- [ ] **Step 2: Wire up auto-fill triggers**

In the `wizardForm()` script in `create.html`, add event listeners to the purchase_price, down_payment, and co_owner_down_payment fields. These fields are in earlier steps, so their `@input` handlers need to call `updateAll()`. Add `@input="updateAll()"` attributes to these fields in steps 3 and 5. This can be done by rendering the form fields manually (not via `{{ form.field }}`) or by adding a global `input` event listener.

The simplest approach: add a delegated event listener in the `init()` method of `wizardForm()`:

```javascript
init() {
  this.$watch('country', () => this.onCountryChange());

  // Delegated input listener for auto-calculations
  const form = document.getElementById('wizard-form');
  if (form) {
    form.addEventListener('input', (e) => {
      const id = e.target.id;
      if (['id_purchase_price', 'id_down_payment', 'id_co_owner_down_payment'].includes(id)) {
        this.updateAll();
      }
      if (id === 'id_mortgage-principal') {
        this._principalDirty = true;
        this.hasMortgage = !!e.target.value;
      }
      if (id === 'id_mortgage-insurance_premium') this._insuranceDirty = true;
      if (id === 'id_co_owner_share') { this._shareDirty = true; }
      if (id === 'id_welcome_tax_paid') this._welcomeTaxDirty = true;
      if (id === 'id_currency') this._currencyDirty = true;
      if (id === 'id_province') this._provinceDirty = true;

      // Sync purchase_date → mortgage start_date
      if (id === 'id_purchase_date') {
        const startEl = document.getElementById('id_mortgage-start_date');
        if (startEl && !startEl.value) startEl.value = e.target.value;
      }
    });
  }
},
```

**Add** this block inside the existing `wizardForm()` `init()` method in `create.html`, after the `$nextTick` error-jump logic and the `$watch('country', ...)` call. Do NOT replace `init()` — append to it.

- [ ] **Step 3: Verify mortgage step with auto-calculations**

Fill step 3 (purchase_price=500000), step 5 (down_payment=100000), then navigate to step 6. Principal should auto-fill as 400000. For a CA property with <20% down, insurance should auto-fill.

- [ ] **Step 4: Commit**

```bash
git add templates/real_estate/partials/wizard_step_6.html templates/real_estate/create.html
git commit -m "feat: add wizard step 6 — mortgage with auto-calculations"
```

---

### Task 8: Step 7 — Review & submit

**Files:**
- Create: `templates/real_estate/partials/wizard_step_7.html`

Summary page showing all entered data organized by section, with "Edit" links that jump back to the relevant step.

- [ ] **Step 1: Create the step 7 partial**

```html
{% load i18n %}

<div data-step="7">
  <div class="mb-6">
    <h2 class="text-2xl font-bold text-text">{% trans "Review your property" %}</h2>
    <p class="mt-2 text-text-muted">
      {% trans "Check that everything looks right before creating your property." %}
    </p>
  </div>

  <div class="space-y-4">
    {# ── Section 1: Property type ── #}
    <div class="rounded-xl border border-border p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-medium uppercase tracking-wide text-text-muted">{% trans "Property" %}</h3>
        <button type="button" @click="step = 1" class="text-xs text-primary-600 hover:text-primary-700 font-medium">{% trans "Edit" %}</button>
      </div>
      <div class="space-y-1 text-sm">
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "Country" %}</span>
          <span class="text-text font-medium" x-text="country === 'FR' ? 'France' : 'Canada'"></span>
        </div>
        <div class="flex justify-between" id="review-property-type">
          <span class="text-text-muted">{% trans "Type" %}</span>
          <span class="text-text font-medium" x-text="document.getElementById('id_property_type')?.selectedOptions[0]?.text || '—'"></span>
        </div>
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "Usage" %}</span>
          <span class="text-text font-medium" x-text="document.getElementById('id_usage')?.selectedOptions[0]?.text || '—'"></span>
        </div>
      </div>
    </div>

    {# ── Section 2: Location ── #}
    <div class="rounded-xl border border-border p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-medium uppercase tracking-wide text-text-muted">{% trans "Location" %}</h3>
        <button type="button" @click="step = 2" class="text-xs text-primary-600 hover:text-primary-700 font-medium">{% trans "Edit" %}</button>
      </div>
      <div class="space-y-1 text-sm">
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "Name" %}</span>
          <span class="text-text font-medium" x-text="document.getElementById('id_name')?.value || '—'"></span>
        </div>
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "Address" %}</span>
          <span class="text-text font-medium" x-text="document.getElementById('id_address')?.value || '—'"></span>
        </div>
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "City" %}</span>
          <span class="text-text font-medium" x-text="document.getElementById('id_city')?.value || '—'"></span>
        </div>
      </div>
    </div>

    {# ── Section 3: Purchase ── #}
    <div class="rounded-xl border border-border p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-medium uppercase tracking-wide text-text-muted">{% trans "Purchase" %}</h3>
        <button type="button" @click="step = 3" class="text-xs text-primary-600 hover:text-primary-700 font-medium">{% trans "Edit" %}</button>
      </div>
      <div class="space-y-1 text-sm">
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "Price" %}</span>
          <span class="text-text font-medium font-mono" x-text="
            (() => {
              const v = document.getElementById('id_purchase_price')?.value;
              return v ? Number(v).toLocaleString('en-CA', {minimumFractionDigits: 0}) : '—';
            })()
          "></span>
        </div>
        <div class="flex justify-between">
          <span class="text-text-muted">{% trans "Date" %}</span>
          <span class="text-text font-medium" x-text="document.getElementById('id_purchase_date')?.value || '—'"></span>
        </div>
      </div>
    </div>

    {# ── Section 4: Mortgage (conditional — uses Alpine-tracked state) ── #}
    <template x-if="hasMortgage">
      <div class="rounded-xl border border-border p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-medium uppercase tracking-wide text-text-muted">{% trans "Mortgage" %}</h3>
          <button type="button" @click="step = 6" class="text-xs text-primary-600 hover:text-primary-700 font-medium">{% trans "Edit" %}</button>
        </div>
        <div class="space-y-1 text-sm">
          <div class="flex justify-between">
            <span class="text-text-muted">{% trans "Principal" %}</span>
            <span class="text-text font-medium font-mono" x-text="
              (() => {
                const v = document.getElementById('id_mortgage-principal')?.value;
                return v ? Number(v).toLocaleString('en-CA', {minimumFractionDigits: 0}) : '—';
              })()
            "></span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-muted">{% trans "Rate" %}</span>
            <span class="text-text font-medium font-mono" x-text="(document.getElementById('id_mortgage-annual_rate')?.value || '—') + '%'"></span>
          </div>
        </div>
      </div>
    </template>

    {# ── Section 5: Ownership (conditional co-owner) ── #}
    <template x-if="hasCoOwner">
      <div class="rounded-xl border border-border p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-medium uppercase tracking-wide text-text-muted">{% trans "Co-ownership" %}</h3>
          <button type="button" @click="step = 5" class="text-xs text-primary-600 hover:text-primary-700 font-medium">{% trans "Edit" %}</button>
        </div>
        <div class="space-y-1 text-sm">
          <div class="flex justify-between">
            <span class="text-text-muted">{% trans "Co-owner" %}</span>
            <span class="text-text font-medium" x-text="document.getElementById('id_co_owner_email')?.value || '—'"></span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-muted">{% trans "Their share" %}</span>
            <span class="text-text font-medium" x-text="(document.getElementById('id_co_owner_share')?.value || '—') + '%'"></span>
          </div>
          <div class="flex justify-between">
            <span class="text-text-muted">{% trans "Your share" %}</span>
            <span class="text-text font-medium" x-text="getYourShare()"></span>
          </div>
        </div>
      </div>
    </template>
  </div>
</div>
```

- [ ] **Step 2: Verify the review step**

Fill out all previous steps, navigate to step 7. Verify the review shows the entered data. Click "Edit" buttons to jump back to correct steps. Click "Create property" to submit the form.

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/wizard_step_7.html
git commit -m "feat: add wizard step 7 — review & submit"
```

---

### Task 9: Test the full wizard flow

**Files:**
- Modify: `apps/real_estate/tests/test_views.py`

Verify the wizard form still works with the existing `property_create` view. The backend receives the same POST data as before — only the template changed.

- [ ] **Step 1: Write tests for wizard form submission**

The existing `test_create_property` and `test_create_property_with_co_owner` tests should already pass since the view and forms are unchanged. Add a test confirming the create template renders with the new wizard structure.

Add to `test_views.py`:

```python
class PropertyCreateWizardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_create_page_renders_wizard(self):
        """The create page should render the wizard shell with progress bar."""
        response = self.client.get(reverse("real_estate:create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "wizardForm")
        self.assertContains(response, "data-step")

    def test_create_form_still_submits(self):
        """The wizard wraps the same form — POST should still work."""
        data = {
            "name": "Test Property",
            "country": "CA",
            "property_type": "house",
            "usage": "primary",
            "currency": "CAD",
            "address": "123 Test St",
            "city": "Montreal",
            "province": "QC",
            "postal_code": "H1A 1A1",
            "purchase_price": "500000",
            "purchase_date": "2024-01-01",
            "down_payment": "100000",
            # Mortgage fields (prefixed)
            "mortgage-lender": "Test Bank",
            "mortgage-principal": "400000",
            "mortgage-annual_rate": "5.5",
            "mortgage-rate_type": "fixed",
            "mortgage-amortization_years": "25",
            "mortgage-term_years": "5",
            "mortgage-payment_frequency": "monthly",
            "mortgage-start_date": "2024-01-01",
            "mortgage-insurance_premium": "0",
        }
        response = self.client.post(reverse("real_estate:create"), data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest apps/real_estate/tests/test_views.py -v -k "wizard"
```

Expected: Both tests PASS.

- [ ] **Step 3: Run the full test suite**

```bash
uv run pytest apps/real_estate/tests/ -v
```

Expected: All existing tests still pass (no backend changes).

- [ ] **Step 4: Commit**

```bash
git add apps/real_estate/tests/test_views.py
git commit -m "test: add wizard form rendering and submission tests"
```

---

### Task 10: Add French translations for wizard strings

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

- [ ] **Step 1: Add translations for new wizard strings**

Run `makemessages` to extract new strings, then translate them:

```bash
uv run python manage.py makemessages -l fr --no-wrap
```

Edit `locale/fr/LC_MESSAGES/django.po` and add French translations for all new wizard strings:

| English | French |
|---------|--------|
| "What kind of property?" | "Quel type de bien ?" |
| "Start by telling us the basics. The country determines tax rules, mortgage calculations, and which fields we'll ask about." | "Commençons par les bases. Le pays détermine les règles fiscales, les calculs hypothécaires et les champs à renseigner." |
| "Where is it located?" | "Où se situe-t-il ?" |
| "The address helps track your property and determines local tax rules." | "L'adresse permet de suivre votre bien et de déterminer les règles fiscales locales." |
| "A friendly name to identify this property" | "Un nom pour identifier facilement ce bien" |
| "Purchase details" | "Détails de l'achat" |
| "These details help calculate your equity, tax obligations, and cost of ownership over time." | "Ces informations permettent de calculer votre équité, vos obligations fiscales et vos coûts de possession." |
| "The total price you paid (or agreed to pay) for the property." | "Le prix total que vous avez payé (ou convenu de payer) pour le bien." |
| "Used to calculate holding period for capital gains tax." | "Utilisé pour calculer la durée de détention pour l'impôt sur les plus-values." |
| "One-time municipal tax on property transfer." | "Taxe municipale unique sur le transfert de propriété." |
| "What's it worth today?" | "Quelle est sa valeur actuelle ?" |
| "These fields are optional. If you know the current value, it helps us show your equity and appreciation over time." | "Ces champs sont facultatifs. Si vous connaissez la valeur actuelle, cela nous permet d'afficher votre équité et l'appréciation dans le temps." |
| "You can skip this step and add valuations later from the property detail page." | "Vous pouvez passer cette étape et ajouter des évaluations plus tard depuis la page du bien." |
| "Your best estimate of the property's current market value." | "Votre meilleure estimation de la valeur marchande actuelle du bien." |
| "From your municipal tax bill." | "Figurant sur votre avis d'imposition municipale." |
| "Who owns this property?" | "Qui est propriétaire ?" |
| "Your down payment is used to calculate the initial mortgage amount and your ownership share if you have a co-owner." | "Votre mise de fonds sert à calculer le montant initial du prêt et votre part de propriété en cas de copropriété." |
| "The amount you put down at purchase. This reduces the mortgage principal." | "Le montant versé à l'achat. Cela réduit le capital du prêt." |
| "I have a co-owner" | "J'ai un copropriétaire" |
| "We'll send them an invitation. They can accept and see the property from their own account." | "Nous leur enverrons une invitation. Ils pourront accepter et voir le bien depuis leur propre compte." |
| "How is it financed?" | "Comment est-il financé ?" |
| "If you have a mortgage, fill in the details below. This lets us generate your full amortization schedule and track equity over time." | "Si vous avez un prêt hypothécaire, remplissez les détails ci-dessous. Cela nous permet de générer votre tableau d'amortissement complet et de suivre votre équité." |
| "No mortgage? Skip this step — you can always add one later." | "Pas de prêt ? Passez cette étape — vous pourrez en ajouter un plus tard." |
| "Auto-calculated from purchase price minus down payments." | "Calculé automatiquement à partir du prix d'achat moins les mises de fonds." |
| "Canadian fixed rates use semi-annual compounding." | "Les taux fixes canadiens utilisent la capitalisation semestrielle." |
| "French rates use simple monthly compounding." | "Les taux français utilisent la capitalisation mensuelle simple." |
| "Typically 25 years in Canada." | "Généralement 25 ans au Canada." |
| "Typically 20-25 years in France." | "Généralement 20-25 ans en France." |
| "Typically 5 years. You'll renew at a new rate when the term ends." | "Généralement 5 ans. Vous renouvellerez à un nouveau taux à la fin du terme." |
| "Usually the same as your purchase date." | "Généralement la même que votre date d'achat." |
| "Review your property" | "Vérifiez votre bien" |
| "Check that everything looks right before creating your property." | "Vérifiez que tout est correct avant de créer votre bien." |
| "Back" | "Retour" |
| "Step %(current)s of %(total)s" | "Étape %(current)s de %(total)s" |
| "Monthly cost" | "Coût mensuel" |
| "My monthly cost" | "Mon coût mensuel" |

- [ ] **Step 2: Compile messages**

```bash
uv run python manage.py compilemessages
```

- [ ] **Step 3: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for wizard form steps"
```

---

## Chunk 2: Monthly Cost Stat Card

### Task 11: Replace "Your Share" stat card with "Monthly Cost"

**Files:**
- Modify: `templates/real_estate/detail.html`

Replace the 4th stat card ("Your share") with a "Monthly cost" card that shows total monthly cost or user's monthly cost based on the toggle.

- [ ] **Step 1: Modify the stat cards grid in detail.html**

Find the 4th card block (the "Your share" card). Replace it with two conditional cards (Total/My Share), following the same pattern as the other 3 cards.

**Remove** (the current card 4):
```html
{% show_money owner_snapshot.your_equity property.currency as share_display %}
{% with pct=owner_snapshot.share_pct|floatformat:0|add:"%" %}
{% include "components/stat_card.html" with label=_("Your share") value=share_display annotation=pct tooltip_id="your_share" tooltip_text=tips.your_share %}
{% endwith %}
```

**Replace with**:
```html
{# Card 4: Monthly cost (replaces "Your share") #}
{% show_money cost_total.total_monthly property.currency as mc_total_display %}
<div x-show="!showMine">
  {% include "components/stat_card.html" with label=_("Monthly cost") value=mc_total_display annotation="" tooltip_id="monthly_cost" tooltip_text=tips.monthly_cost %}
</div>
{% if has_co_owners %}
  {% show_money cost_mine.your_total_monthly property.currency as mc_mine_display %}
  <div x-show="showMine" x-cloak>
    {% include "components/stat_card.html" with label=_("My monthly cost") value=mc_mine_display annotation=owner_pct tooltip_id="monthly_cost" tooltip_text=tips.monthly_cost %}
  </div>
{% endif %}
```

- [ ] **Step 2: Move ownership % to the Value card annotation (My Share mode)**

When "My Share" is toggled, the Value card's annotation should show the ownership percentage instead of appreciation %. This replaces the information previously shown in the "Your Share" card.

Find the "My Share" version of Card 1 (Value) — it's the `x-show="showMine"` block for the first card. The full block to change looks like:

**Before** (the entire My Share Value card block):
```html
{% with pct=snapshot.appreciation_pct|signed_pct %}
{% include "components/stat_card.html" with label=_("Your value") value=yval_display annotation=pct tooltip_id="value" tooltip_text=tips.value %}
{% endwith %}
```

**After** (use `owner_pct` from the `{% with %}` wrapper added in Step 3):
```html
{% include "components/stat_card.html" with label=_("Your value") value=yval_display annotation=owner_pct tooltip_id="value" tooltip_text=tips.value %}
```

This way, the Value card shows:
- Total mode: "$500,000" with "+10.5% appreciation" annotation
- My Share mode: "$250,000" with "50%" ownership annotation

- [ ] **Step 3: Define `owner_pct` template variable**

In `detail.html`, add the `{% with %}` tag immediately before the `<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">` line, and close `{% endwith %}` immediately after the closing `</div>` of that grid:

```html
{% with owner_pct=owner_snapshot.share_pct|floatformat:0|add:"%" %}
<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
  {# ... all 4 stat cards ... #}
</div>
{% endwith %}
```

This wraps only the stat cards grid, keeping the scope tight.

- [ ] **Step 4: Verify the stat cards visually**

Navigate to a property detail page. Verify:
- 4 cards displayed: Value, Equity, Mortgage, Monthly Cost
- Toggle to "My Share": cards show user-specific values, Value card shows ownership %, Monthly Cost shows user's cost
- No more "Your Share" card with duplicate equity value

- [ ] **Step 5: Commit**

```bash
git add templates/real_estate/detail.html
git commit -m "feat: replace 'Your Share' stat card with 'Monthly Cost'"
```

---

### Task 12: Verify HTMX monthly cost card still works

**No file changes.** The monthly cost stat card uses server-rendered values on page load. The detailed monthly cost breakdown card below it still updates via HTMX events. The stat card value refreshes on full page reload — this is acceptable since the breakdown card provides real-time updates.

- [ ] **Step 1: Verify HTMX events still work**

Navigate to a property detail page. Add an expense. Verify the monthly cost breakdown card (below the stat cards) updates via HTMX. The stat card at the top will refresh on page reload.

---

### Task 13: Verify "Monthly cost" tooltip text exists

**Files:**
- Verify: `apps/real_estate/tooltips.py`

The `monthly_cost` key already exists in `TERM_TOOLTIPS` (around line 85). No change needed — just verify it renders.

- [ ] **Step 1: Verify the tooltip renders on the stat card**

Navigate to a property detail page. Hover over the `?` icon on the Monthly Cost stat card. The tooltip should display the existing educational text about total monthly cost of ownership.

---

### Task 14: Test the stat card replacement

**Files:**
- Modify: `apps/real_estate/tests/test_views.py`

- [ ] **Step 1: Update existing tests that check for "Your share"**

Search `test_views.py` for any assertion that checks for the "Your share" stat card. Add a test for "Monthly cost" to the existing `TestPropertyDetail` class (or equivalent), matching the project's pytest fixture injection style:

```python
def test_detail_page_shows_monthly_cost_card(self, client, prop, mortgage):
    """Detail page should show Monthly Cost stat card instead of Your Share."""
    response = client.get(f"/real-estate/{prop.pk}/")
    assert response.status_code == 200
    assert b"Monthly cost" in response.content
```

Note: Do NOT assert "Your share" is absent — the string may still appear in tooltips or other contexts. Only verify the new card is present. The `mortgage` fixture is needed because the detail view uses it for snapshot calculations.

- [ ] **Step 2: Run the tests**

```bash
uv run pytest apps/real_estate/tests/test_views.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Run the full suite**

```bash
uv run pytest -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add apps/real_estate/tests/test_views.py
git commit -m "test: update stat card assertions for monthly cost replacement"
```

---

### Task 15: Final integration verification

- [ ] **Step 1: Manual test — wizard create (Canada)**

1. Navigate to `/real-estate/create/`
2. Step 1: Select Canada, House, Primary → Next
3. Step 2: Fill name, address, city, QC, postal → Next
4. Step 3: Price 500000, date 2024-01-01 → Next
5. Step 4: Skip (all optional) → Next
6. Step 5: Down payment 100000, no co-owner → Next
7. Step 6: Fill mortgage (principal auto-fills 400000, insurance auto-calcs) → Next
8. Step 7: Review all data → Create property
9. Verify redirect to detail page with 4 stat cards: Value, Equity, Mortgage, Monthly Cost

- [ ] **Step 2: Manual test — wizard create (France, with co-owner)**

1. Step 1: France, Condo, Rental → Next
2. Step 2: Name, address, city, département=75, postal → Next
3. Step 3: Price 300000, date 2023-06-01, frais de notaire auto-fills (24000) → Next
4. Step 4: Current valuation 320000 → Next
5. Step 5: Down payment 60000, add co-owner with email + down payment → Next
6. Step 6: Mortgage with borrower insurance rate visible, term_years hidden → Next
7. Step 7: Review shows co-owner section → Create property
8. Verify detail page: toggle to "My Share", Monthly Cost card shows user's cost, Value card shows ownership %

- [ ] **Step 3: Manual test — wizard back navigation & validation**

1. Navigate to step 4, click "Back" → step 3 shows with previously entered data preserved
2. Navigate forward → data still there
3. On step 1, click "Next" without selecting property type → required field highlighted
4. Submit the form from step 7 with a required field missing → server-side error, wizard jumps to correct step

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest -v
```

Expected: All tests pass (both existing and new).

- [ ] **Step 5: Final commit (if any remaining changes)**

```bash
git add -A
git commit -m "feat: complete real estate wizard form and monthly cost stat card"
```
