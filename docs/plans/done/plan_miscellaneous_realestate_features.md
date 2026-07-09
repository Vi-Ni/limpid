# Real Estate — Miscellaneous Features Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 8 new features to the real estate module: rate change simulation, rental income tracking, monthly cost summary, my-share toggle, per-owner payment customization, property deletion, expense proof links, and evolution line charts.

**Architecture:** All features extend the existing real_estate app. New models for rate changes, rental income, and owner payment splits. New service functions for monthly cost calculation and amortization with rate changes. Line charts use Chart.js (already available) with a new `initLineCharts()` module. The "my share" toggle uses Alpine.js session-less client-side state. Property deletion is a simple view + confirmation template.

**Tech Stack:** Django 5.2, HTMX 2, Alpine.js 3, Chart.js 4 (LineController, LineElement, PointElement, CategoryScale, LinearScale), Tailwind CSS v4

---

## Todo List

### Phase 1: Models & Migration (Tasks 1–5)

Data layer — new models, new field, admin registration, and migration.

- [x] **Task 1 — MortgageRateChange model**
  - [ ] 1.1 Write failing test (`TestMortgageRateChange`: str, ordering)
  - [ ] 1.2 Run test → confirm ImportError
  - [ ] 1.3 Write model in `models.py` (FK to Mortgage, `rate_changes` related_name)
  - [ ] 1.4 `makemigrations` + run test → PASS
  - [ ] 1.5 Commit
- [x] **Task 2 — RentalIncome model**
  - [ ] 2.1 Write failing test (`TestRentalIncome`: str, net_monthly_rent, no agency)
  - [ ] 2.2 Run test → confirm FAIL
  - [ ] 2.3 Write model in `models.py` (FK to Property, `rental_incomes` related_name, `net_monthly_rent` property)
  - [ ] 2.4 Run test → PASS
  - [ ] 2.5 Commit
- [x] **Task 3 — OwnerMonthlyPayment model**
  - [ ] 3.1 Write failing test (`TestOwnerMonthlyPayment`: str, unique_together constraint)
  - [ ] 3.2 Run test → confirm FAIL
  - [ ] 3.3 Write model in `models.py` (FK to Mortgage + PropertyOwnership, `owner_payments` related_name)
  - [ ] 3.4 Run test → PASS
  - [ ] 3.5 Commit
- [x] **Task 4 — proof_link field on PropertyExpense**
  - [ ] 4.1 Write failing test (`TestExpenseProofLink`: optional, stores URL)
  - [ ] 4.2 Run test → confirm FAIL
  - [ ] 4.3 Add `proof_link = URLField(blank=True, default="")` to PropertyExpense
  - [ ] 4.4 `makemigrations` + run test → PASS
  - [ ] 4.5 Commit
- [x] **Task 5 — Register new models in admin**
  - [ ] 5.1 Add `MortgageRateChangeAdmin`, `RentalIncomeAdmin`, `OwnerMonthlyPaymentAdmin` to `admin.py`
  - [ ] 5.2 `manage.py check` → no issues
  - [ ] 5.3 Commit

### Phase 2: Service Layer (Tasks 6–8)

Core business logic — amortization with rate changes, monthly cost calculation, chart data generation.

- [x] **Task 6 — Amortization schedule with rate changes**
  - [ ] 6.1 Write failing tests (`TestAmortizationWithRateChanges`: original rate before change, recalculated payment after, ends at zero, no changes = same, simulation flag)
  - [ ] 6.2 Run tests → confirm FAIL
  - [ ] 6.3 Modify `generate_amortization_schedule()` to load `mortgage.rate_changes`, recalculate payment at each rate change date
  - [ ] 6.4 Run new tests → PASS
  - [ ] 6.5 Run all existing amortization tests → no regressions
  - [ ] 6.6 Commit
- [x] **Task 7 — Monthly cost calculation service**
  - [ ] 7.1 Write failing tests (`TestMonthlyCost`: basic, with rental income, no mortgage, owner share)
  - [ ] 7.2 Run tests → confirm FAIL
  - [ ] 7.3 Write `calculate_monthly_cost(prop, for_user=None)` in `services.py` (mortgage + taxes/12 + recurring expenses/12 - rental net; per-user with custom OwnerMonthlyPayment)
  - [ ] 7.4 Run tests → PASS
  - [ ] 7.5 Commit
- [x] **Task 8 — Evolution chart data generation**
  - [ ] 8.1 Write failing tests (`TestEvolutionChartData`: monthly series, principal exceeds interest, balance decreases)
  - [ ] 8.2 Run tests → confirm FAIL
  - [ ] 8.3 Write `generate_evolution_chart_data(mortgage)` in `services.py` (labels, principal/interest/balance/payment series)
  - [ ] 8.4 Run tests → PASS
  - [ ] 8.5 Commit

### Phase 3: Forms & Views (Tasks 9–11)

Django forms, views, URL patterns, and context updates.

- [x] **Task 9 — Add new forms**
  - [ ] 9.1 Add `RateChangeForm` (with `TAILWIND_SELECT_CLASS` for rate_type select)
  - [ ] 9.2 Add `RentalIncomeForm`
  - [ ] 9.3 Add `OwnerMonthlyPaymentForm` (with `prop` kwarg to filter owner queryset)
  - [ ] 9.4 Add `proof_link` field + widget to existing `ExpenseForm`
  - [ ] 9.5 Add model imports (`MortgageRateChange`, `RentalIncome`, `OwnerMonthlyPayment`)
  - [ ] 9.6 Verify no syntax errors
  - [ ] 9.7 Commit
- [x] **Task 10 — Add new views + URL patterns**
  - [ ] 10.1 `delete_property` view (admin-only, POST to delete, GET for confirmation)
  - [ ] 10.2 `add_rate_change` / `delete_rate_change` HTMX views
  - [ ] 10.3 `add_rental_income` / `delete_rental_income` HTMX views
  - [ ] 10.4 `monthly_cost_partial` view (with `?mine=1` toggle)
  - [ ] 10.5 `owner_payments` view (POST to save, renders form + list)
  - [ ] 10.6 Add imports (`HttpResponseForbidden`, new forms, new models, new services)
  - [ ] 10.7 Add all URL patterns to `urls.py`
  - [ ] 10.8 `manage.py check` → no issues
  - [ ] 10.9 Commit
- [x] **Task 11 — Update property_detail context**
  - [ ] 11.1 Add `monthly_cost`, `evolution_chart`, `rental_incomes`, `owner_payment_form` to context
  - [ ] 11.2 Run existing detail view tests → no regressions
  - [ ] 11.3 Commit

### Phase 4: Templates (Tasks 12–19)

All template work — new partials and updates to existing templates.

- [x] **Task 12 — confirm_delete_property.html**
  - [x] 12.1 Write template (card with warning, csrf form, cancel link)
  - [x] 12.2 Commit
- [x] **Task 13 — monthly_cost.html partial**
  - [x] 13.1 Write template (metric rows for mortgage, taxes, recurring, rental; net total with `show_mine` toggle)
  - [x] 13.2 Commit
- [x] **Task 14 — rate_change_list.html + rate_change_form.html**
  - [x] 14.1 Write list partial (loop with rate, date, simulation badge, HTMX delete)
  - [x] 14.2 Write form partial (HTMX post, grid fields, cancel button)
  - [x] 14.3 Commit
- [x] **Task 15 — rental_income_list.html + rental_income_form.html**
  - [x] 15.1 Write list partial (loop with rent, agency %, dates, HTMX delete)
  - [x] 15.2 Write form partial (HTMX post, grid fields)
  - [x] 15.3 Commit
- [x] **Task 16 — owner_payments_form.html**
  - [x] 16.1 Write template (existing payments list + HTMX form to add new split)
  - [x] 16.2 Commit
- [x] **Task 17 — Update detail.html** (largest template change)
  - [x] 17.1 Add delete button in header (admin-only)
  - [x] 17.2 Add Alpine.js my-share toggle (`x-data`, `x-show`) around stat cards
  - [x] 17.3 Add monthly cost card (with `{% include %}` + HTMX mine toggle)
  - [x] 17.4 Add rental income section in right column (for `usage == "rental"`)
  - [x] 17.5 Add rate change section inside mortgage card
  - [x] 17.6 Add payment split section inside mortgage card (if co-owners)
  - [x] 17.7 Add evolution line chart canvas section
  - [x] 17.8 Commit
- [x] **Task 18 — Update expense templates with proof_link**
  - [x] 18.1 Add proof link icon/column to `expense_list.html`
  - [x] 18.2 Verify form auto-renders proof_link (uses `{% for field in form %}`)
  - [x] 18.3 Commit
- [x] **Task 19 — Update list.html with monthly cost**
  - [x] 19.1 Add `calculate_monthly_cost` call in `property_list` view loop
  - [x] 19.2 Add monthly cost row to property cards in `list.html`
  - [x] 19.3 Commit

### Phase 5: Frontend — Line Charts (Task 20)

Chart.js line chart module for amortization evolution curves.

- [x] **Task 20 — evolution.js + main.js update**
  - [x] 20.1 Write `evolution.js` (tree-shaken Chart.js imports, dual Y-axis, downsampling, principal/interest/balance datasets)
  - [x] 20.2 Import `initEvolutionCharts` in `main.js`, add to DOMContentLoaded + htmx:afterSwap
  - [x] 20.3 `npm run build` → succeeds
  - [x] 20.4 Commit

### Phase 6: Tooltips, Translations & Tests (Tasks 21–24)

Polish layer — tooltips, i18n, view tests, and final integration pass.

- [x] **Task 21 — Add tooltip texts**
  - [x] 21.1 Add entries to `TERM_TOOLTIPS`: monthly_cost, net_monthly_cost, rate_change, rental_income, payment_split
  - [x] 21.2 Commit
- [x] **Task 22 — Add view tests**
  - [x] 22.1 Add imports for new models in `test_views.py`
  - [x] 22.2 Write `TestDeleteProperty` (admin delete, confirmation page, non-owner 404)
  - [x] 22.3 Write `TestRateChangeViews` (add, delete)
  - [x] 22.4 Write `TestRentalIncomeViews` (add)
  - [x] 22.5 Write `TestMonthlyCostView` (partial, mine toggle)
  - [x] 22.6 Run tests → PASS
  - [x] 22.7 Commit
- [x] **Task 23 — French translations**
  - [x] 23.1 `makemessages -l fr` to extract new strings
  - [x] 23.2 Translate all ~40 new strings in `django.po`
  - [x] 23.3 `compilemessages`
  - [x] 23.4 Commit
- [x] **Task 24 — Final integration**
  - [x] 24.1 `pytest --cov=apps -v` → all tests PASS (201 tests)
  - [x] 24.2 `ruff check . && ruff format --check .` → clean
  - [x] 24.3 `npm run build` → succeeds
  - [x] 24.4 Manual smoke test (detail page, list page, FR locale)
  - [x] 24.5 Final commit if any fixes needed

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `apps/real_estate/migrations/0007_rate_rental_payments_prooflink.py` | Migration for all new models/fields |
| `frontend/src/charts/evolution.js` | Chart.js line chart module for amortization evolution curves |
| `templates/real_estate/partials/monthly_cost.html` | Monthly cost summary partial (HTMX target) |
| `templates/real_estate/partials/owner_payments_form.html` | Per-owner monthly payment split form |
| `templates/real_estate/partials/rate_change_form.html` | Rate change form partial |
| `templates/real_estate/partials/rate_change_list.html` | Rate change list partial |
| `templates/real_estate/partials/rental_income_form.html` | Rental income form partial |
| `templates/real_estate/partials/rental_income_list.html` | Rental income list partial |
| `templates/real_estate/confirm_delete_property.html` | Delete property confirmation page |

### Modified files
| File | Changes |
|------|---------|
| `apps/real_estate/models.py` | Add `MortgageRateChange`, `RentalIncome`, `OwnerMonthlyPayment` models. Add `proof_link` field to `PropertyExpense`. |
| `apps/real_estate/forms.py` | Add `RateChangeForm`, `RentalIncomeForm`, `OwnerMonthlyPaymentForm`. Add `proof_link` to `ExpenseForm`. |
| `apps/real_estate/services.py` | Add `generate_amortization_schedule_with_rate_changes()`, `calculate_monthly_cost()`, `generate_evolution_chart_data()`. Modify `get_owner_snapshot()` to use `OwnerMonthlyPayment`. |
| `apps/real_estate/views.py` | Add views: `delete_property`, `add_rate_change`, `edit_rate_change`, `delete_rate_change`, `add_rental_income`, `edit_rental_income`, `delete_rental_income`, `monthly_cost_partial`, `owner_payments`. |
| `apps/real_estate/urls.py` | Add URL patterns for all new views. |
| `apps/real_estate/tooltips.py` | Add tooltip texts for new concepts (rate_change, rental_income, monthly_cost, net_monthly_cost). |
| `apps/real_estate/admin.py` | Register new models. |
| `apps/real_estate/templatetags/real_estate_filters.py` | No changes needed. |
| `templates/real_estate/detail.html` | Add monthly cost card, my-share toggle, line chart section, rental income section, delete button. |
| `templates/real_estate/list.html` | Show monthly cost on property cards. |
| `templates/real_estate/amortization.html` | Support rate changes in schedule, add evolution chart. |
| `templates/real_estate/partials/expense_list.html` | Show proof_link column. |
| `templates/real_estate/partials/expense_form.html` | Add proof_link field. |
| `frontend/src/main.js` | Import and init `evolution.js` line charts. |
| `locale/fr/LC_MESSAGES/django.po` | Add French translations for all new strings. |
| `apps/real_estate/tests/test_models.py` | Tests for new models. |
| `apps/real_estate/tests/test_services.py` | Tests for new service functions. |
| `apps/real_estate/tests/test_views.py` | Tests for new views. |

---

## Chunk 1: Models & Migration

### Task 1: Add MortgageRateChange model

Allows tracking rate changes over time (renewals or simulated rate scenarios).

**Files:**
- Modify: `apps/real_estate/models.py` (insert after Mortgage class, ~line 197)
- Test: `apps/real_estate/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_models.py, add at end of file:

class TestMortgageRateChange:
    @pytest.fixture
    def rate_change(self, mortgage):
        from apps.real_estate.models import MortgageRateChange

        return MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.500"),
            new_rate_type="fixed",
            effective_date=date(2025, 1, 1),
            note="Term renewal",
        )

    def test_str(self, rate_change):
        assert "4.500" in str(rate_change)
        assert "2025-01-01" in str(rate_change)

    def test_ordering(self, mortgage):
        from apps.real_estate.models import MortgageRateChange

        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.000"),
            effective_date=date(2026, 1, 1),
        )
        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("5.500"),
            effective_date=date(2025, 1, 1),
        )
        changes = list(MortgageRateChange.objects.filter(mortgage=mortgage))
        assert changes[0].effective_date < changes[1].effective_date
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_models.py::TestMortgageRateChange -v`
Expected: FAIL — `ImportError: cannot import name 'MortgageRateChange'`

- [ ] **Step 3: Write the model**

In `apps/real_estate/models.py`, insert after the Mortgage class (after line 197):

```python
class MortgageRateChange(models.Model):
    """Track rate changes over time (renewals or simulated scenarios)."""

    mortgage = models.ForeignKey(Mortgage, on_delete=models.CASCADE, related_name="rate_changes")
    new_annual_rate = models.DecimalField(_("new annual rate (%)"), max_digits=5, decimal_places=3)
    new_rate_type = models.CharField(
        _("new rate type"), max_length=20, choices=Mortgage.RATE_TYPE_CHOICES, blank=True, default=""
    )
    effective_date = models.DateField(_("effective date"))
    is_simulation = models.BooleanField(_("simulation only"), default=False)
    note = models.CharField(_("note"), max_length=200, blank=True)

    class Meta:
        ordering = ["effective_date"]
        verbose_name = _("mortgage rate change")
        verbose_name_plural = _("mortgage rate changes")

    def __str__(self):
        return f"{self.new_annual_rate}% from {self.effective_date}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python manage.py makemigrations real_estate --name rate_rental_payments_prooflink && uv run pytest apps/real_estate/tests/test_models.py::TestMortgageRateChange -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/real_estate/models.py apps/real_estate/tests/test_models.py apps/real_estate/migrations/
git commit -m "feat: add MortgageRateChange model for rate renewal tracking"
```

---

### Task 2: Add RentalIncome model

Tracks monthly rental income and optional agency fees for rental properties.

**Files:**
- Modify: `apps/real_estate/models.py` (insert after PropertyTax class, ~line 295)
- Test: `apps/real_estate/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_models.py, add:

class TestRentalIncome:
    @pytest.fixture
    def rental_prop(self, user):
        p = Property.objects.create(
            name="Rental Unit",
            property_type="condo",
            usage="rental",
            address="456 Rent St",
            city="Montreal",
            purchase_price=Decimal("400000"),
            purchase_date=date(2020, 1, 1),
            current_valuation=Decimal("420000"),
            valuation_date=date(2024, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=p, is_admin=True)
        return p

    @pytest.fixture
    def rental_income(self, rental_prop):
        from apps.real_estate.models import RentalIncome

        return RentalIncome.objects.create(
            property=rental_prop,
            monthly_rent=Decimal("1800"),
            agency_fee_pct=Decimal("8.0"),
            start_date=date(2021, 1, 1),
        )

    def test_str(self, rental_income):
        assert "1800" in str(rental_income)

    def test_net_monthly_rent(self, rental_income):
        # 1800 - (1800 * 8%) = 1800 - 144 = 1656
        assert rental_income.net_monthly_rent == Decimal("1656.00")

    def test_net_monthly_rent_no_agency(self, rental_prop):
        from apps.real_estate.models import RentalIncome

        ri = RentalIncome.objects.create(
            property=rental_prop,
            monthly_rent=Decimal("1800"),
            agency_fee_pct=Decimal("0"),
            start_date=date(2021, 1, 1),
        )
        assert ri.net_monthly_rent == Decimal("1800.00")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_models.py::TestRentalIncome -v`
Expected: FAIL

- [ ] **Step 3: Write the model**

In `apps/real_estate/models.py`, insert after the PropertyTax class:

```python
class RentalIncome(models.Model):
    """Track rental income for investment properties."""

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rental_incomes")
    monthly_rent = models.DecimalField(_("monthly rent"), max_digits=10, decimal_places=2)
    agency_fee_pct = models.DecimalField(
        _("agency fee (%)"), max_digits=5, decimal_places=2, default=0,
        help_text=_("Percentage taken by rental management agency"),
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"), null=True, blank=True)
    note = models.CharField(_("note"), max_length=200, blank=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = _("rental income")
        verbose_name_plural = _("rental incomes")

    def __str__(self):
        return f"{self.monthly_rent}/mo from {self.start_date}"

    @property
    def net_monthly_rent(self):
        fee = self.monthly_rent * self.agency_fee_pct / 100
        return (self.monthly_rent - fee).quantize(Decimal("0.01"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest apps/real_estate/tests/test_models.py::TestRentalIncome -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/real_estate/models.py apps/real_estate/tests/test_models.py
git commit -m "feat: add RentalIncome model for rental properties"
```

---

### Task 3: Add OwnerMonthlyPayment model

Allows customizing how much each co-owner contributes per month to the mortgage, independent of their ownership share.

**Files:**
- Modify: `apps/real_estate/models.py` (insert after MortgagePayment class, ~line 217)
- Test: `apps/real_estate/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_models.py, add:

class TestOwnerMonthlyPayment:
    @pytest.fixture
    def owner_payment(self, prop, user, mortgage):
        from apps.real_estate.models import OwnerMonthlyPayment

        ownership = PropertyOwnership.objects.get(user=user, property=prop)
        return OwnerMonthlyPayment.objects.create(
            mortgage=mortgage,
            owner=ownership,
            monthly_amount=Decimal("1500"),
            effective_date=date(2020, 1, 1),
        )

    def test_str(self, owner_payment):
        assert "1500" in str(owner_payment)

    def test_unique_effective_date(self, prop, user, mortgage):
        from apps.real_estate.models import OwnerMonthlyPayment

        ownership = PropertyOwnership.objects.get(user=user, property=prop)
        OwnerMonthlyPayment.objects.create(
            mortgage=mortgage, owner=ownership,
            monthly_amount=Decimal("1500"), effective_date=date(2020, 1, 1),
        )
        with pytest.raises(IntegrityError):
            OwnerMonthlyPayment.objects.create(
                mortgage=mortgage, owner=ownership,
                monthly_amount=Decimal("1600"), effective_date=date(2020, 1, 1),
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_models.py::TestOwnerMonthlyPayment -v`
Expected: FAIL

- [ ] **Step 3: Write the model**

In `apps/real_estate/models.py`, insert after the MortgagePayment class:

```python
class OwnerMonthlyPayment(models.Model):
    """Track how much each co-owner contributes monthly to the mortgage."""

    mortgage = models.ForeignKey(Mortgage, on_delete=models.CASCADE, related_name="owner_payments")
    owner = models.ForeignKey(PropertyOwnership, on_delete=models.CASCADE, related_name="monthly_payments")
    monthly_amount = models.DecimalField(_("monthly amount"), max_digits=10, decimal_places=2)
    effective_date = models.DateField(_("effective date"))
    note = models.CharField(_("note"), max_length=200, blank=True)

    class Meta:
        ordering = ["effective_date"]
        unique_together = [("mortgage", "owner", "effective_date")]
        verbose_name = _("owner monthly payment")
        verbose_name_plural = _("owner monthly payments")

    def __str__(self):
        return f"{self.owner.user.email}: {self.monthly_amount}/mo from {self.effective_date}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest apps/real_estate/tests/test_models.py::TestOwnerMonthlyPayment -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/real_estate/models.py apps/real_estate/tests/test_models.py
git commit -m "feat: add OwnerMonthlyPayment model for co-owner payment tracking"
```

---

### Task 4: Add proof_link field to PropertyExpense

A URL field to link to a Google Drive (or other) document proving the expense.

**Files:**
- Modify: `apps/real_estate/models.py` (add field to PropertyExpense, after line 240)
- Test: `apps/real_estate/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_models.py, add:

class TestExpenseProofLink:
    def test_proof_link_optional(self, prop, user):
        ownership = PropertyOwnership.objects.get(user=user, property=prop)
        expense = PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="New roof",
            amount=Decimal("15000"),
            date=date(2024, 6, 1),
            paid_by=ownership,
        )
        assert expense.proof_link == ""

    def test_proof_link_stores_url(self, prop, user):
        ownership = PropertyOwnership.objects.get(user=user, property=prop)
        expense = PropertyExpense.objects.create(
            property=prop,
            expense_type="renovation",
            description="New roof",
            amount=Decimal("15000"),
            date=date(2024, 6, 1),
            paid_by=ownership,
            proof_link="https://drive.google.com/file/d/abc123",
        )
        assert expense.proof_link == "https://drive.google.com/file/d/abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_models.py::TestExpenseProofLink -v`
Expected: FAIL

- [ ] **Step 3: Add the field**

In `apps/real_estate/models.py`, add after the `increases_acb` field in PropertyExpense (after line 240):

```python
    proof_link = models.URLField(_("proof document link"), max_length=500, blank=True, default="")
```

- [ ] **Step 4: Generate migration and run tests**

Run: `uv run python manage.py makemigrations real_estate && uv run pytest apps/real_estate/tests/test_models.py::TestExpenseProofLink -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/real_estate/models.py apps/real_estate/tests/test_models.py apps/real_estate/migrations/
git commit -m "feat: add proof_link URL field to PropertyExpense"
```

---

### Task 5: Register new models in admin

**Files:**
- Modify: `apps/real_estate/admin.py`

- [ ] **Step 1: Add admin registrations**

In `apps/real_estate/admin.py`, add imports and registrations:

```python
# Add to imports (line 3):
from .models import MortgageRateChange, OwnerMonthlyPayment, RentalIncome

# Add at end of file:

@admin.register(MortgageRateChange)
class MortgageRateChangeAdmin(admin.ModelAdmin):
    list_display = ("mortgage", "new_annual_rate", "effective_date", "is_simulation")
    list_filter = ("is_simulation",)


@admin.register(RentalIncome)
class RentalIncomeAdmin(admin.ModelAdmin):
    list_display = ("property", "monthly_rent", "agency_fee_pct", "start_date", "end_date")


@admin.register(OwnerMonthlyPayment)
class OwnerMonthlyPaymentAdmin(admin.ModelAdmin):
    list_display = ("mortgage", "owner", "monthly_amount", "effective_date")
```

- [ ] **Step 2: Verify admin loads**

Run: `uv run python manage.py check`
Expected: System check identified no issues.

- [ ] **Step 3: Commit**

```bash
git add apps/real_estate/admin.py
git commit -m "feat: register new models in admin"
```

---

## Chunk 2: Service Layer — Rate Changes & Monthly Cost

### Task 6: Amortization schedule with rate changes

The core financial function: generate a schedule that switches rates at specified dates.

**Files:**
- Modify: `apps/real_estate/services.py` (add new function after `generate_amortization_schedule`, ~line 78)
- Test: `apps/real_estate/tests/test_services.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_services.py, add new test class:

class TestAmortizationWithRateChanges:
    @pytest.fixture
    def rate_change(self, mortgage):
        from apps.real_estate.models import MortgageRateChange

        return MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("4.000"),
            new_rate_type="fixed",
            effective_date=date(2025, 1, 1),
        )

    def test_schedule_uses_original_rate_before_change(self, mortgage, rate_change):
        from apps.real_estate.services import generate_amortization_schedule

        schedule = generate_amortization_schedule(mortgage)
        # Payment in 2020 (before change) should use 5% rate
        jan_2020 = next(e for e in schedule if e["date"].year == 2020 and e["date"].month == 2)
        # Payment in 2025 (after change) should use 4% rate → lower interest
        feb_2025 = next(e for e in schedule if e["date"].year == 2025 and e["date"].month == 2)
        assert feb_2025["interest"] < jan_2020["interest"]

    def test_schedule_recalculates_payment_after_change(self, mortgage, rate_change):
        from apps.real_estate.services import generate_amortization_schedule

        schedule = generate_amortization_schedule(mortgage)
        before = next(e for e in schedule if e["date"] == date(2024, 12, 1))
        after = next(e for e in schedule if e["date"] == date(2025, 2, 1))
        # Lower rate → lower total payment
        assert after["total_payment"] < before["total_payment"]

    def test_schedule_ends_at_zero_balance(self, mortgage, rate_change):
        from apps.real_estate.services import generate_amortization_schedule

        schedule = generate_amortization_schedule(mortgage)
        assert schedule[-1]["balance"] == Decimal("0")

    def test_no_rate_changes_same_as_original(self, mortgage):
        from apps.real_estate.services import generate_amortization_schedule

        schedule = generate_amortization_schedule(mortgage)
        # Without rate changes, behavior unchanged
        assert schedule[0]["interest"] > schedule[0]["principal"]

    def test_simulation_flag_included(self, mortgage):
        from apps.real_estate.models import MortgageRateChange

        MortgageRateChange.objects.create(
            mortgage=mortgage,
            new_annual_rate=Decimal("6.000"),
            effective_date=date(2025, 6, 1),
            is_simulation=True,
        )
        from apps.real_estate.services import generate_amortization_schedule

        schedule = generate_amortization_schedule(mortgage)
        assert schedule[-1]["balance"] == Decimal("0")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_services.py::TestAmortizationWithRateChanges -v`
Expected: FAIL (rate changes exist in DB but schedule ignores them)

- [ ] **Step 3: Modify `generate_amortization_schedule` to support rate changes**

Replace the existing `generate_amortization_schedule` function in `apps/real_estate/services.py` (lines 31-78):

```python
def generate_amortization_schedule(mortgage):
    """Generate month-by-month amortization schedule, with rate changes if any."""
    country = mortgage.real_estate.country
    rate_type = mortgage.rate_type
    annual_rate = mortgage.annual_rate
    n_total = mortgage.amortization_years * 12
    balance = mortgage.effective_principal
    start = mortgage.start_date

    # Load rate changes sorted by date
    rate_changes = list(mortgage.rate_changes.order_by("effective_date"))
    change_idx = 0

    # Calculate initial monthly rate and payment
    r = calculate_monthly_rate(annual_rate, rate_type, country)
    insurance_monthly = Decimal("0")
    if mortgage.borrower_insurance_rate:
        insurance_monthly = (mortgage.effective_principal * mortgage.borrower_insurance_rate / 100 / 12).quantize(
            Decimal("0.01")
        )

    # Calculate initial payment
    schedule = []
    r = calculate_monthly_rate(annual_rate, rate_type, country)
    remaining = n_total
    if r == 0:
        pmt = balance / remaining
    else:
        pmt = ((r * balance) / (1 - (1 + r) ** (-remaining))).quantize(Decimal("0.01"))

    change_idx = 0

    for i in range(1, n_total + 1):
        payment_date = start + relativedelta(months=i)

        # Apply rate changes
        recalc = False
        while change_idx < len(rate_changes) and rate_changes[change_idx].effective_date <= payment_date:
            rc = rate_changes[change_idx]
            annual_rate = rc.new_annual_rate
            if rc.new_rate_type:
                rate_type = rc.new_rate_type
            r = calculate_monthly_rate(annual_rate, rate_type, country)
            recalc = True
            change_idx += 1

        if recalc:
            remaining = n_total - i + 1
            if r == 0:
                pmt = balance / remaining
            else:
                pmt = ((r * balance) / (1 - (1 + r) ** (-remaining))).quantize(Decimal("0.01"))

        interest = (balance * r).quantize(Decimal("0.01"))
        principal_portion = pmt - interest

        if balance - principal_portion < Decimal("0.01"):
            principal_portion = balance
            pmt = principal_portion + interest

        balance = max(balance - principal_portion, Decimal("0"))

        schedule.append({
            "payment_number": i,
            "date": payment_date,
            "total_payment": pmt + insurance_monthly,
            "principal": principal_portion,
            "interest": interest,
            "insurance": insurance_monthly,
            "balance": balance,
        })

        if balance == 0:
            break

    return schedule
```

**Important:** The above is the conceptual approach. The actual implementation should replace the existing function body (lines 31-78) with the rate-change-aware version. The key changes:
1. Load `mortgage.rate_changes.order_by("effective_date")` at the start
2. Before each payment, check if any rate change has `effective_date <= payment_date`
3. When a rate change applies: update `annual_rate`, `rate_type`, recalculate `r` (monthly rate) and `pmt` (payment) for remaining balance and remaining months

- [ ] **Step 4: Run tests**

Run: `uv run pytest apps/real_estate/tests/test_services.py::TestAmortizationWithRateChanges -v`
Expected: PASS

- [ ] **Step 5: Run all existing amortization tests to check no regression**

Run: `uv run pytest apps/real_estate/tests/test_services.py -v -k "Amortization or MonthlyRate or MonthlyPayment or RemainingBalance or TotalPaid"`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add apps/real_estate/services.py apps/real_estate/tests/test_services.py
git commit -m "feat: support rate changes in amortization schedule"
```

---

### Task 7: Monthly cost calculation service

Calculates the total monthly cost of owning a property: mortgage payment + taxes/12 + expenses/12 - rental income.

**Files:**
- Modify: `apps/real_estate/services.py`
- Test: `apps/real_estate/tests/test_services.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_services.py, add:

class TestMonthlyCost:
    @pytest.fixture
    def prop_with_taxes(self, prop, mortgage):
        from apps.real_estate.models import PropertyTax

        PropertyTax.objects.create(property=prop, tax_type="municipal", year=2025, amount=Decimal("4200"))
        PropertyTax.objects.create(property=prop, tax_type="school", year=2025, amount=Decimal("600"))
        return prop

    def test_monthly_cost_basic(self, prop_with_taxes, mortgage):
        from apps.real_estate.services import calculate_monthly_cost

        result = calculate_monthly_cost(prop_with_taxes)
        assert "mortgage_payment" in result
        assert "taxes_monthly" in result
        assert "total_monthly" in result
        # Taxes: (4200 + 600) / 12 = 400
        assert result["taxes_monthly"] == Decimal("400.00")

    def test_monthly_cost_with_rental_income(self, prop):
        from apps.real_estate.models import RentalIncome

        prop.usage = "rental"
        prop.save()
        RentalIncome.objects.create(
            property=prop, monthly_rent=Decimal("2000"),
            agency_fee_pct=Decimal("10"), start_date=date(2020, 1, 1),
        )
        from apps.real_estate.services import calculate_monthly_cost

        result = calculate_monthly_cost(prop)
        assert result["rental_income"] == Decimal("2000.00")
        assert result["rental_net"] == Decimal("1800.00")
        assert result["total_monthly"] < result["mortgage_payment"] + result["taxes_monthly"]

    def test_monthly_cost_no_mortgage(self, prop):
        from apps.real_estate.services import calculate_monthly_cost

        # Delete mortgages
        prop.mortgages.all().delete()
        result = calculate_monthly_cost(prop)
        assert result["mortgage_payment"] == Decimal("0")

    def test_monthly_cost_owner_share(self, prop_with_taxes, mortgage, user):
        from apps.real_estate.services import calculate_monthly_cost

        result = calculate_monthly_cost(prop_with_taxes, for_user=user)
        assert "your_total_monthly" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_services.py::TestMonthlyCost -v`
Expected: FAIL

- [ ] **Step 3: Write the service function**

Add to `apps/real_estate/services.py`:

```python
def calculate_monthly_cost(prop, for_user=None):
    """Calculate the total monthly cost of owning a property.

    Returns dict with: mortgage_payment, taxes_monthly, insurance_monthly,
    recurring_expenses_monthly, rental_income, rental_net, total_monthly.
    If for_user is provided, also includes your_total_monthly based on ownership share
    or custom OwnerMonthlyPayment records.
    """
    from .models import OwnerMonthlyPayment, RentalIncome

    TWO_PLACES = Decimal("0.01")

    # Mortgage
    mortgage_payment = Decimal("0")
    for m in prop.mortgages.filter(is_active=True):
        mortgage_payment += m.monthly_payment

    # Taxes: sum latest year's taxes, divide by 12
    from django.db.models import Max

    latest_year = prop.taxes.aggregate(Max("year"))["year__max"]
    taxes_annual = Decimal("0")
    if latest_year:
        taxes_annual = sum(t.amount for t in prop.taxes.filter(year=latest_year))
    taxes_monthly = (taxes_annual / 12).quantize(TWO_PLACES)

    # Recurring expenses (condo_fees, charges_copro, insurance) — averaged over 12 months
    recurring_types = {"condo_fees", "charges_copro", "insurance"}
    from django.db.models import Sum
    import datetime

    one_year_ago = datetime.date.today() - datetime.timedelta(days=365)
    recurring_total = (
        prop.expenses.filter(expense_type__in=recurring_types, date__gte=one_year_ago)
        .aggregate(Sum("amount"))["amount__sum"]
        or Decimal("0")
    )
    recurring_monthly = (recurring_total / 12).quantize(TWO_PLACES)

    # Rental income (use most recent active entry)
    rental_income = Decimal("0")
    rental_net = Decimal("0")
    active_rental = (
        RentalIncome.objects.filter(property=prop, end_date__isnull=True).order_by("-start_date").first()
    )
    if not active_rental:
        active_rental = RentalIncome.objects.filter(property=prop).order_by("-start_date").first()
    if active_rental:
        rental_income = active_rental.monthly_rent
        rental_net = active_rental.net_monthly_rent

    total_monthly = (mortgage_payment + taxes_monthly + recurring_monthly - rental_net).quantize(TWO_PLACES)

    result = {
        "mortgage_payment": mortgage_payment.quantize(TWO_PLACES),
        "taxes_monthly": taxes_monthly,
        "recurring_expenses_monthly": recurring_monthly,
        "rental_income": rental_income,
        "rental_net": rental_net,
        "total_monthly": total_monthly,
    }

    # Per-user cost
    if for_user:
        ownership = prop.ownerships.filter(user=for_user).first()
        if ownership:
            shares = get_current_ownership_shares(prop)
            share_pct = shares.get(ownership, Decimal("100")) / 100

            # Check for custom payment split
            your_mortgage = Decimal("0")
            for m in prop.mortgages.all():
                custom = (
                    OwnerMonthlyPayment.objects.filter(
                        mortgage=m, owner=ownership, effective_date__lte=datetime.date.today()
                    )
                    .order_by("-effective_date")
                    .first()
                )
                if custom:
                    your_mortgage += custom.monthly_amount
                else:
                    your_mortgage += (m.monthly_payment * share_pct).quantize(TWO_PLACES)

            your_taxes = (taxes_monthly * share_pct).quantize(TWO_PLACES)
            your_recurring = (recurring_monthly * share_pct).quantize(TWO_PLACES)
            your_rental_offset = (rental_net * share_pct).quantize(TWO_PLACES)
            your_total = (your_mortgage + your_taxes + your_recurring - your_rental_offset).quantize(TWO_PLACES)

            result["your_mortgage_payment"] = your_mortgage
            result["your_taxes_monthly"] = your_taxes
            result["your_total_monthly"] = your_total

    return result
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest apps/real_estate/tests/test_services.py::TestMonthlyCost -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/real_estate/services.py apps/real_estate/tests/test_services.py
git commit -m "feat: add monthly cost calculation service"
```

---

### Task 8: Evolution chart data generation

Generate data for line charts showing principal vs interest crossover and monthly payment evolution over time.

**Files:**
- Modify: `apps/real_estate/services.py`
- Test: `apps/real_estate/tests/test_services.py`

- [ ] **Step 1: Write the failing test**

```python
# In test_services.py, add:

class TestEvolutionChartData:
    def test_generates_monthly_series(self, mortgage):
        from apps.real_estate.services import generate_evolution_chart_data

        data = generate_evolution_chart_data(mortgage)
        assert "labels" in data
        assert "principal_series" in data
        assert "interest_series" in data
        assert "balance_series" in data
        assert len(data["labels"]) > 0
        assert len(data["principal_series"]) == len(data["labels"])

    def test_principal_eventually_exceeds_interest(self, mortgage):
        from apps.real_estate.services import generate_evolution_chart_data

        data = generate_evolution_chart_data(mortgage)
        # At some point, principal > interest
        crossover_found = False
        for p, i in zip(data["principal_series"], data["interest_series"]):
            if p > i:
                crossover_found = True
                break
        assert crossover_found

    def test_balance_decreases(self, mortgage):
        from apps.real_estate.services import generate_evolution_chart_data

        data = generate_evolution_chart_data(mortgage)
        assert data["balance_series"][0] > data["balance_series"][-1]
        assert data["balance_series"][-1] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/real_estate/tests/test_services.py::TestEvolutionChartData -v`
Expected: FAIL

- [ ] **Step 3: Write the service function**

Add to `apps/real_estate/services.py`:

```python
def generate_evolution_chart_data(mortgage):
    """Generate time series data for amortization evolution line charts.

    Returns dict with:
    - labels: list of date strings (YYYY-MM)
    - principal_series: monthly principal portions
    - interest_series: monthly interest portions
    - balance_series: remaining balance after each payment
    - payment_series: total payment amounts (useful when rate changes occur)
    """
    schedule = generate_amortization_schedule(mortgage)

    labels = []
    principal_series = []
    interest_series = []
    balance_series = []
    payment_series = []

    for entry in schedule:
        labels.append(entry["date"].strftime("%Y-%m"))
        principal_series.append(float(entry["principal"]))
        interest_series.append(float(entry["interest"]))
        balance_series.append(float(entry["balance"]))
        payment_series.append(float(entry["total_payment"]))

    return {
        "labels": labels,
        "principal_series": principal_series,
        "interest_series": interest_series,
        "balance_series": balance_series,
        "payment_series": payment_series,
    }
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest apps/real_estate/tests/test_services.py::TestEvolutionChartData -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/real_estate/services.py apps/real_estate/tests/test_services.py
git commit -m "feat: add evolution chart data generation for amortization"
```

---

## Chunk 3: Forms & Views

### Task 9: Add new forms

**Files:**
- Modify: `apps/real_estate/forms.py`

- [ ] **Step 1: Add RateChangeForm**

Add after InviteCoOwnerForm (end of file):

```python
class RateChangeForm(forms.ModelForm):
    class Meta:
        model = MortgageRateChange
        fields = ["new_annual_rate", "new_rate_type", "effective_date", "is_simulation", "note"]
        widgets = {
            "new_annual_rate": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.001"}),
            "new_rate_type": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "effective_date": forms.DateInput(attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}, format="%Y-%m-%d"),
            "is_simulation": forms.CheckboxInput(attrs={"class": "rounded border-border text-primary-600 focus:ring-primary-500"}),
            "note": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["effective_date"].localize = False
```

- [ ] **Step 2: Add RentalIncomeForm**

```python
class RentalIncomeForm(forms.ModelForm):
    class Meta:
        model = RentalIncome
        fields = ["monthly_rent", "agency_fee_pct", "start_date", "end_date", "note"]
        widgets = {
            "monthly_rent": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "agency_fee_pct": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "start_date": forms.DateInput(attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}, format="%Y-%m-%d"),
            "note": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].localize = False
        self.fields["end_date"].localize = False
        self.fields["end_date"].required = False
```

- [ ] **Step 3: Add OwnerMonthlyPaymentForm**

```python
class OwnerMonthlyPaymentForm(forms.ModelForm):
    class Meta:
        model = OwnerMonthlyPayment
        fields = ["owner", "monthly_amount", "effective_date", "note"]
        widgets = {
            "owner": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
            "monthly_amount": forms.NumberInput(attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.01"}),
            "effective_date": forms.DateInput(attrs={"class": TAILWIND_INPUT_CLASS, "type": "date"}, format="%Y-%m-%d"),
            "note": forms.TextInput(attrs={"class": TAILWIND_INPUT_CLASS}),
        }

    def __init__(self, *args, prop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["effective_date"].localize = False
        if prop:
            self.fields["owner"].queryset = prop.ownerships.all()
            self.fields["owner"].label_from_instance = lambda o: o.user.get_full_name() or o.user.email
```

- [ ] **Step 4: Add proof_link to ExpenseForm**

In the existing `ExpenseForm.Meta.fields` list (currently `["expense_type", "description", "amount", "date", "increases_acb"]`), add `"proof_link"`:

```python
fields = ["expense_type", "description", "amount", "date", "increases_acb", "proof_link"]
```

And add the widget:

```python
"proof_link": forms.URLInput(attrs={"class": TAILWIND_INPUT_CLASS, "placeholder": "https://drive.google.com/..."}),
```

- [ ] **Step 5: Add model imports at top of forms.py**

```python
from .models import MortgageRateChange, OwnerMonthlyPayment, RentalIncome
```

- [ ] **Step 6: Verify no syntax errors**

Run: `uv run python -c "from apps.real_estate.forms import RateChangeForm, RentalIncomeForm, OwnerMonthlyPaymentForm"`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add apps/real_estate/forms.py
git commit -m "feat: add forms for rate changes, rental income, owner payments, and expense proof link"
```

---

### Task 10: Add new views

**Files:**
- Modify: `apps/real_estate/views.py`
- Modify: `apps/real_estate/urls.py`

- [ ] **Step 1: Add delete_property view**

```python
@login_required
def delete_property(request, pk):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    ownership = prop.ownerships.get(user=request.user)
    if not ownership.is_admin:
        return HttpResponseForbidden()
    if request.method == "POST":
        prop.delete()
        messages.success(request, _("Property deleted."))
        return redirect("real_estate:list")
    return render(request, "real_estate/confirm_delete_property.html", {"property": prop})
```

- [ ] **Step 2: Add rate change CRUD views**

```python
@login_required
def add_rate_change(request, pk, mortgage_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    form = RateChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rc = form.save(commit=False)
        rc.mortgage = mortgage
        rc.save()
        rate_changes = mortgage.rate_changes.all()
        return render(request, "real_estate/partials/rate_change_list.html", {"rate_changes": rate_changes, "property": prop, "mortgage": mortgage})
    return render(request, "real_estate/partials/rate_change_form.html", {"form": form, "property": prop, "mortgage": mortgage})


@login_required
def delete_rate_change(request, pk, mortgage_id, rc_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    rc = get_object_or_404(MortgageRateChange, pk=rc_id, mortgage=mortgage)
    if request.method == "DELETE":
        rc.delete()
    rate_changes = mortgage.rate_changes.all()
    return render(request, "real_estate/partials/rate_change_list.html", {"rate_changes": rate_changes, "property": prop, "mortgage": mortgage})
```

- [ ] **Step 3: Add rental income CRUD views**

```python
@login_required
def add_rental_income(request, pk):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    form = RentalIncomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ri = form.save(commit=False)
        ri.property = prop
        ri.save()
        notify_co_owners(prop, request.user, "property_updated", _("Rental income updated"))
        incomes = prop.rental_incomes.all()
        return render(request, "real_estate/partials/rental_income_list.html", {"rental_incomes": incomes, "property": prop})
    return render(request, "real_estate/partials/rental_income_form.html", {"form": form, "property": prop})


@login_required
def delete_rental_income(request, pk, income_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    income = get_object_or_404(RentalIncome, pk=income_id, property=prop)
    if request.method == "DELETE":
        income.delete()
    incomes = prop.rental_incomes.all()
    return render(request, "real_estate/partials/rental_income_list.html", {"rental_incomes": incomes, "property": prop})
```

- [ ] **Step 4: Add monthly cost partial view**

```python
@login_required
def monthly_cost_partial(request, pk):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    show_mine = request.GET.get("mine") == "1"
    cost = calculate_monthly_cost(prop, for_user=request.user if show_mine else None)
    return render(request, "real_estate/partials/monthly_cost.html", {
        "cost": cost, "property": prop, "show_mine": show_mine,
    })
```

- [ ] **Step 5: Add owner payments view**

```python
@login_required
def owner_payments(request, pk, mortgage_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    form = OwnerMonthlyPaymentForm(request.POST or None, prop=prop)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False)
        payment.mortgage = mortgage
        payment.save()
        notify_co_owners(prop, request.user, "property_updated", _("Payment split updated"))
    payments = mortgage.owner_payments.select_related("owner__user").all()
    return render(request, "real_estate/partials/owner_payments_form.html", {
        "form": OwnerMonthlyPaymentForm(prop=prop),
        "payments": payments, "property": prop, "mortgage": mortgage,
    })
```

- [ ] **Step 6: Update imports in views.py**

Add at top:

```python
from django.http import HttpResponseForbidden
from .forms import RateChangeForm, RentalIncomeForm, OwnerMonthlyPaymentForm
from .models import MortgageRateChange, RentalIncome
from .services import calculate_monthly_cost, generate_evolution_chart_data
```

- [ ] **Step 7: Add URL patterns**

In `apps/real_estate/urls.py`, add these patterns (before the closing `]`):

```python
    path("<int:pk>/delete/", views.delete_property, name="delete"),
    path("<int:pk>/mortgage/<int:mortgage_id>/rate-change/", views.add_rate_change, name="add_rate_change"),
    path("<int:pk>/mortgage/<int:mortgage_id>/rate-change/<int:rc_id>/delete/", views.delete_rate_change, name="delete_rate_change"),
    path("<int:pk>/rental-income/", views.add_rental_income, name="add_rental_income"),
    path("<int:pk>/rental-income/<int:income_id>/delete/", views.delete_rental_income, name="delete_rental_income"),
    path("<int:pk>/monthly-cost/", views.monthly_cost_partial, name="monthly_cost"),
    path("<int:pk>/mortgage/<int:mortgage_id>/owner-payments/", views.owner_payments, name="owner_payments"),
```

- [ ] **Step 8: Verify no import errors**

Run: `uv run python manage.py check`
Expected: No issues

- [ ] **Step 9: Commit**

```bash
git add apps/real_estate/views.py apps/real_estate/urls.py
git commit -m "feat: add views for delete, rate changes, rental income, monthly cost, owner payments"
```

---

### Task 11: Update property_detail view to pass new context

**Files:**
- Modify: `apps/real_estate/views.py` (property_detail function, lines 92-171)

- [ ] **Step 1: Add monthly cost and evolution chart to detail context**

In the `property_detail` view, add after the chart JSON generation (around line 160):

```python
    # Monthly cost
    monthly_cost = calculate_monthly_cost(prop, for_user=request.user)

    # Evolution chart data
    evolution_chart = None
    if mortgage:
        evolution_chart = json.dumps(generate_evolution_chart_data(mortgage))

    # Rental incomes
    rental_incomes = prop.rental_incomes.all()

    # Owner payment form (for the payment split section)
    owner_payment_form = None
    if mortgage:
        owner_payment_form = OwnerMonthlyPaymentForm(prop=prop)
```

And add to the context dict:

```python
    "monthly_cost": monthly_cost,
    "evolution_chart": evolution_chart,
    "rental_incomes": rental_incomes,
    "owner_payment_form": owner_payment_form,
```

- [ ] **Step 2: Verify view works**

Run: `uv run pytest apps/real_estate/tests/test_views.py::TestPropertyDetail -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/real_estate/views.py
git commit -m "feat: pass monthly cost and evolution chart to detail context"
```

---

## Chunk 4: Templates

### Task 12: Create confirm_delete_property template

**Files:**
- Create: `templates/real_estate/confirm_delete_property.html`

- [ ] **Step 1: Write the template**

```django
{% extends "base.html" %}
{% load i18n %}

{% block content %}
<div class="container-limpid py-6 animate-enter">
  <div class="max-w-md mx-auto">
    {% include "components/card_start.html" with title=_("Delete property") variant="warning" %}
      <p class="text-sm text-text mb-4">
        {% blocktrans with name=property.name %}Are you sure you want to delete <strong>{{ name }}</strong>? This will permanently remove all associated mortgages, expenses, valuations, taxes, and co-ownership data.{% endblocktrans %}
      </p>
      <p class="text-sm text-danger-600 font-medium mb-4">{% trans "This action cannot be undone." %}</p>
      <form method="post">
        {% csrf_token %}
        <div class="flex items-center gap-3">
          <button type="submit" class="btn-danger">{% trans "Delete permanently" %}</button>
          <a href="{% url 'real_estate:detail' property.pk %}" class="btn-ghost">{% trans "Cancel" %}</a>
        </div>
      </form>
    {% include "components/card_end.html" %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/real_estate/confirm_delete_property.html
git commit -m "feat: add property deletion confirmation template"
```

---

### Task 13: Create monthly cost partial template

**Files:**
- Create: `templates/real_estate/partials/monthly_cost.html`

- [ ] **Step 1: Write the template**

```django
{% load i18n real_estate_filters %}

<div class="space-y-0">
  {% show_money cost.mortgage_payment property.currency as mp %}
  {% include "components/metric_row.html" with label=_("Mortgage") value=mp %}

  {% show_money cost.taxes_monthly property.currency as tx %}
  {% include "components/metric_row.html" with label=_("Taxes (monthly)") value=tx %}

  {% if cost.recurring_expenses_monthly %}
  {% show_money cost.recurring_expenses_monthly property.currency as re %}
  {% include "components/metric_row.html" with label=_("Recurring expenses") value=re %}
  {% endif %}

  {% if cost.rental_income %}
  {% show_money cost.rental_net property.currency as rn %}
  <div class="flex items-baseline justify-between py-2.5 border-b border-border/60">
    <span class="text-sm text-text-muted">{% trans "Rental income (net)" %}</span>
    <span class="text-sm font-mono tabular-nums text-success-600">- {{ rn }}</span>
  </div>
  {% endif %}

  <div class="flex items-baseline justify-between py-3 mt-1">
    <span class="text-sm font-semibold text-text">
      {% if show_mine %}{% trans "Your net monthly cost" %}{% else %}{% trans "Net monthly cost" %}{% endif %}
    </span>
    {% if show_mine %}
      {% show_money cost.your_total_monthly property.currency as total %}
    {% else %}
      {% show_money cost.total_monthly property.currency as total %}
    {% endif %}
    <span class="text-lg font-semibold font-mono tabular-nums {% if cost.total_monthly > 0 %}text-danger-600{% else %}text-success-600{% endif %}">
      {{ total }}
    </span>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add templates/real_estate/partials/monthly_cost.html
git commit -m "feat: add monthly cost summary partial template"
```

---

### Task 14: Create rate change list and form partials

**Files:**
- Create: `templates/real_estate/partials/rate_change_list.html`
- Create: `templates/real_estate/partials/rate_change_form.html`

- [ ] **Step 1: Write rate_change_list.html**

```django
{% load i18n real_estate_filters %}

{% if rate_changes %}
<div class="space-y-2">
  {% for rc in rate_changes %}
  <div class="flex items-center justify-between py-2 border-b border-border/60 group">
    <div>
      <span class="font-mono text-sm font-semibold">{{ rc.new_annual_rate }}%</span>
      {% if rc.new_rate_type %}<span class="text-xs text-text-muted ml-1">({{ rc.get_new_rate_type_display }})</span>{% endif %}
      <span class="text-xs text-text-muted ml-2">{% trans "from" %} {{ rc.effective_date }}</span>
      {% if rc.is_simulation %}{% include "components/badge.html" with label=_("Simulation") variant="warning" %}{% endif %}
    </div>
    <button hx-delete="{% url 'real_estate:delete_rate_change' property.pk mortgage.pk rc.pk %}"
            hx-target="#rate-change-list" hx-swap="innerHTML" hx-confirm="{% trans 'Delete this rate change?' %}"
            class="text-xs text-danger-500 hover:text-danger-700 opacity-0 group-hover:opacity-100 transition-opacity">
      {% trans "Delete" %}
    </button>
  </div>
  {% endfor %}
</div>
{% else %}
<p class="text-sm text-text-muted">{% trans "No rate changes scheduled." %}</p>
{% endif %}
```

- [ ] **Step 2: Write rate_change_form.html**

```django
{% load i18n %}

<form hx-post="{% url 'real_estate:add_rate_change' property.pk mortgage.pk %}"
      hx-target="#rate-change-list" hx-swap="innerHTML" class="mt-4 space-y-3">
  {% csrf_token %}
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    {% for field in form %}
    <div>
      <label class="block text-xs text-text-muted mb-1">{{ field.label }}</label>
      {{ field }}
      {% for error in field.errors %}<p class="text-xs text-danger-600 mt-1">{{ error }}</p>{% endfor %}
    </div>
    {% endfor %}
  </div>
  <div class="flex items-center gap-2">
    <button type="submit" class="btn-primary text-sm">{% trans "Add rate change" %}</button>
    <button type="button" onclick="this.closest('form').remove()" class="btn-ghost text-sm">{% trans "Cancel" %}</button>
  </div>
</form>
```

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/rate_change_list.html templates/real_estate/partials/rate_change_form.html
git commit -m "feat: add rate change list and form partials"
```

---

### Task 15: Create rental income list and form partials

**Files:**
- Create: `templates/real_estate/partials/rental_income_list.html`
- Create: `templates/real_estate/partials/rental_income_form.html`

- [ ] **Step 1: Write rental_income_list.html**

```django
{% load i18n real_estate_filters %}

{% if rental_incomes %}
<div class="space-y-2">
  {% for ri in rental_incomes %}
  <div class="flex items-center justify-between py-2 border-b border-border/60 group">
    <div>
      {% show_money ri.monthly_rent property.currency as rent_display %}
      <span class="font-mono text-sm font-semibold">{{ rent_display }}/{% trans "mo" %}</span>
      {% if ri.agency_fee_pct %}<span class="text-xs text-text-muted ml-1">({% trans "agency" %}: {{ ri.agency_fee_pct }}%)</span>{% endif %}
      <span class="text-xs text-text-muted ml-2">{% trans "from" %} {{ ri.start_date }}</span>
      {% if ri.end_date %}<span class="text-xs text-text-muted">→ {{ ri.end_date }}</span>{% endif %}
    </div>
    <button hx-delete="{% url 'real_estate:delete_rental_income' property.pk ri.pk %}"
            hx-target="#rental-income-list" hx-swap="innerHTML" hx-confirm="{% trans 'Delete this rental income?' %}"
            class="text-xs text-danger-500 hover:text-danger-700 opacity-0 group-hover:opacity-100 transition-opacity">
      {% trans "Delete" %}
    </button>
  </div>
  {% endfor %}
</div>
{% else %}
<p class="text-sm text-text-muted">{% trans "No rental income recorded." %}</p>
{% endif %}
```

- [ ] **Step 2: Write rental_income_form.html**

```django
{% load i18n %}

<form hx-post="{% url 'real_estate:add_rental_income' property.pk %}"
      hx-target="#rental-income-list" hx-swap="innerHTML" class="mt-4 space-y-3">
  {% csrf_token %}
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
    {% for field in form %}
    <div>
      <label class="block text-xs text-text-muted mb-1">{{ field.label }}</label>
      {{ field }}
      {% for error in field.errors %}<p class="text-xs text-danger-600 mt-1">{{ error }}</p>{% endfor %}
    </div>
    {% endfor %}
  </div>
  <div class="flex items-center gap-2">
    <button type="submit" class="btn-primary text-sm">{% trans "Add" %}</button>
    <button type="button" onclick="this.closest('form').remove()" class="btn-ghost text-sm">{% trans "Cancel" %}</button>
  </div>
</form>
```

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/rental_income_list.html templates/real_estate/partials/rental_income_form.html
git commit -m "feat: add rental income list and form partials"
```

---

### Task 16: Create owner payments form partial

**Files:**
- Create: `templates/real_estate/partials/owner_payments_form.html`

- [ ] **Step 1: Write the template**

```django
{% load i18n real_estate_filters %}

{% if payments %}
<div class="space-y-2 mb-4">
  {% for p in payments %}
  <div class="flex items-center justify-between py-2 border-b border-border/60">
    <div>
      <span class="text-sm">{{ p.owner.user.get_full_name|default:p.owner.user.email }}</span>
      {% show_money p.monthly_amount property.currency as pmt_display %}
      <span class="font-mono text-sm font-semibold ml-2">{{ pmt_display }}/{% trans "mo" %}</span>
      <span class="text-xs text-text-muted ml-2">{% trans "from" %} {{ p.effective_date }}</span>
    </div>
  </div>
  {% endfor %}
</div>
{% endif %}

<form hx-post="{% url 'real_estate:owner_payments' property.pk mortgage.pk %}"
      hx-target="#owner-payments-container" hx-swap="innerHTML" class="space-y-3">
  {% csrf_token %}
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    {% for field in form %}
    <div>
      <label class="block text-xs text-text-muted mb-1">{{ field.label }}</label>
      {{ field }}
      {% for error in field.errors %}<p class="text-xs text-danger-600 mt-1">{{ error }}</p>{% endfor %}
    </div>
    {% endfor %}
  </div>
  <button type="submit" class="btn-primary text-sm">{% trans "Set payment split" %}</button>
</form>
```

- [ ] **Step 2: Commit**

```bash
git add templates/real_estate/partials/owner_payments_form.html
git commit -m "feat: add owner monthly payment form partial"
```

---

### Task 17: Update detail.html with all new features

This is the biggest template change: add monthly cost card, my-share toggle, delete button, rental income section, rate change section, and evolution chart.

**Files:**
- Modify: `templates/real_estate/detail.html`

- [ ] **Step 1: Add delete button to header (after Edit button, ~line 24)**

Insert inside the header div (after the edit link, before `</div>`):

```django
      {% if ownership.is_admin %}
        <a href="{% url 'real_estate:delete' property.pk %}" class="btn-ghost text-danger-500 hover:text-danger-700 text-sm">{% trans "Delete" %}</a>
      {% endif %}
```

- [ ] **Step 2: Add my-share toggle to stat cards section**

Wrap the stat cards section and the details card in an Alpine.js `x-data` scope. Before line 28 (`{# Stat cards row #}`), add:

```django
  <div x-data="{ showMine: false }">
  {# Toggle: Total vs My share #}
  <div class="flex justify-end mb-2">
    <button @click="showMine = !showMine"
            class="btn-ghost text-xs"
            x-text="showMine ? '{% trans "Show total" %}' : '{% trans "Show my share" %}'">
    </button>
  </div>
```

Then close the `</div>` for `x-data` after the stat cards `</div>` (after line 42). The stat cards themselves use `x-show` to toggle between total and per-owner values:

```django
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    <div x-show="!showMine">
      {% show_money snapshot.current_valuation property.currency as val_display %}
      {% include "components/stat_card.html" with label=_("Value") value=val_display tooltip_id="value" tooltip_text=tips.value %}
    </div>
    <div x-show="showMine">
      {% show_money owner_snapshot.your_valuation property.currency as yval_display %}
      {% include "components/stat_card.html" with label=_("Your value") value=yval_display %}
    </div>

    <div x-show="!showMine">
      {% show_money snapshot.equity property.currency as eq_display %}
      {% with pct=snapshot.equity_pct|floatformat:1|add:"%" %}
      {% include "components/stat_card.html" with label=_("Equity") value=eq_display annotation=pct tooltip_id="equity" tooltip_text=tips.equity %}
      {% endwith %}
    </div>
    <div x-show="showMine">
      {% show_money owner_snapshot.your_equity property.currency as yeq_display %}
      {% include "components/stat_card.html" with label=_("Your equity") value=yeq_display %}
    </div>

    <div x-show="!showMine">
      {% show_money snapshot.mortgage_balance property.currency as mort_display %}
      {% include "components/stat_card.html" with label=_("Mortgage") value=mort_display tooltip_id="mortgage" tooltip_text=tips.mortgage %}
    </div>
    <div x-show="showMine">
      {% show_money owner_snapshot.your_mortgage_share property.currency as ymort_display %}
      {% include "components/stat_card.html" with label=_("Your mortgage") value=ymort_display %}
    </div>

    {% show_money owner_snapshot.your_equity property.currency as share_display %}
    {% with pct=owner_snapshot.share_pct|floatformat:0|add:"%" %}
    {% include "components/stat_card.html" with label=_("Your share") value=share_display annotation=pct tooltip_id="your_share" tooltip_text=tips.your_share %}
    {% endwith %}
  </div>
  </div>
```

- [ ] **Step 3: Add monthly cost card (after charts section, before sale simulator)**

Insert after the charts grid (after line 81):

```django
      {# Monthly cost #}
      {% include "components/card_start.html" with title=_("Monthly Cost") tooltip_id="monthly_cost" tooltip_text=tips.monthly_cost %}
        <div class="flex justify-end mb-2">
          <button hx-get="{% url 'real_estate:monthly_cost' property.pk %}?mine=1"
                  hx-target="#monthly-cost-content" hx-swap="innerHTML"
                  class="btn-ghost text-xs" id="toggle-my-cost">
            {% trans "Show my share" %}
          </button>
        </div>
        <div id="monthly-cost-content">
          {% include "real_estate/partials/monthly_cost.html" with cost=monthly_cost %}
        </div>
      {% include "components/card_end.html" %}
```

- [ ] **Step 4: Add rental income section (for rental properties, in the right column)**

Insert after the Mortgage card section (after line 208):

```django
      {# Rental Income (if rental property) #}
      {% if property.usage == "rental" %}
      {% include "components/card_start.html" with title=_("Rental Income") %}
        <div id="rental-income-list">
          {% include "real_estate/partials/rental_income_list.html" %}
        </div>
        <div class="mt-4 pt-4 border-t border-border">
          <button hx-get="{% url 'real_estate:add_rental_income' property.pk %}"
                  hx-target="#rental-income-form-container" hx-swap="innerHTML"
                  class="btn-ghost text-primary-600 hover:text-primary-700">
            {% trans "+ Add rental income" %}
          </button>
          <div id="rental-income-form-container"></div>
        </div>
      {% include "components/card_end.html" %}
      {% endif %}
```

- [ ] **Step 5: Add rate change section inside the mortgage card**

Insert inside the mortgage card (after the amortization link, before `{% include "components/card_end.html" %}`):

```django
        <div class="mt-4 pt-4 border-t border-border">
          <h4 class="text-xs font-medium uppercase tracking-wide text-text-muted mb-2">{% trans "Rate Changes" %}</h4>
          <div id="rate-change-list">
            {% include "real_estate/partials/rate_change_list.html" with rate_changes=mortgage.rate_changes.all %}
          </div>
          <button hx-get="{% url 'real_estate:add_rate_change' property.pk mortgage.pk %}"
                  hx-target="#rate-change-form-container" hx-swap="innerHTML"
                  class="mt-2 btn-ghost text-primary-600 hover:text-primary-700 text-sm">
            {% trans "+ Add rate change" %}
          </button>
          <div id="rate-change-form-container"></div>
        </div>

        {% if shares|length > 1 %}
        <div class="mt-4 pt-4 border-t border-border">
          <h4 class="text-xs font-medium uppercase tracking-wide text-text-muted mb-2">{% trans "Payment Split" %}</h4>
          <div id="owner-payments-container">
            {% include "real_estate/partials/owner_payments_form.html" with payments=mortgage.owner_payments.all form=owner_payment_form %}
          </div>
        </div>
        {% endif %}
```

- [ ] **Step 6: Add evolution line chart section (after the doughnut charts)**

Insert after the doughnut charts grid (after line 81):

```django
      {# Evolution Charts #}
      {% if evolution_chart %}
      {% include "components/card_start.html" with title=_("Amortization Evolution") %}
        <canvas data-chart="evolution" data-chart-data='{{ evolution_chart }}'
                style="max-height: 300px;"></canvas>
      {% include "components/card_end.html" %}
      {% endif %}
```

- [ ] **Step 7: Commit**

```bash
git add templates/real_estate/detail.html
git commit -m "feat: update detail template with monthly cost, my-share toggle, rate changes, rental income, delete, evolution chart"
```

---

### Task 18: Update expense templates with proof_link

**Files:**
- Modify: `templates/real_estate/partials/expense_list.html`
- Modify: `templates/real_estate/partials/expense_form.html`

- [ ] **Step 1: Add proof link column to expense_list.html**

In the expense table, add an icon link after the amount column. After the `<td>` for amount, add:

```django
      <td class="px-3 py-2 text-right">
        {% if expense.proof_link %}
        <a href="{{ expense.proof_link }}" target="_blank" rel="noopener"
           class="text-primary-600 hover:text-primary-700" title="{% trans 'View proof' %}">
          <svg class="inline h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        </a>
        {% endif %}
      </td>
```

- [ ] **Step 2: The proof_link field is already included in ExpenseForm from Task 9**

The form template uses `{% for field in form %}` which automatically renders all form fields, so the proof_link field will appear in the form without template changes.

- [ ] **Step 3: Commit**

```bash
git add templates/real_estate/partials/expense_list.html
git commit -m "feat: show proof document link in expense list"
```

---

### Task 19: Update list.html with monthly cost

**Files:**
- Modify: `templates/real_estate/list.html`

- [ ] **Step 1: Add monthly cost to property cards**

In the property_list view (`views.py`), the `summaries` list already contains `snapshot` per item. Ensure `monthly_cost` is also computed and added to each item in the list view (modify `property_list` view):

```python
# In property_list view, modify the existing loop (lines 43-46 in views.py):
for prop in properties:
    snapshot = get_owner_snapshot(prop, request.user)
    cost = calculate_monthly_cost(prop, for_user=request.user)
    summaries.append({"property": prop, "snapshot": snapshot, "monthly_cost": cost})
```

Then in `list.html`, add a line to each card showing monthly cost:

```django
      <div class="flex items-baseline justify-between">
        <span class="text-sm text-text-muted">{% trans "Monthly cost" %}</span>
        <span class="font-mono text-sm {% if item.monthly_cost.total_monthly > 0 %}text-danger-600{% else %}text-success-600{% endif %}">
          {% show_money item.monthly_cost.your_total_monthly item.property.currency as mc_display %}
          {{ mc_display }}
        </span>
      </div>
```

- [ ] **Step 2: Commit**

```bash
git add templates/real_estate/list.html apps/real_estate/views.py
git commit -m "feat: show monthly cost on property list cards"
```

---

## Chunk 5: Frontend — Line Charts

### Task 20: Create evolution line chart module

**Files:**
- Create: `frontend/src/charts/evolution.js`
- Modify: `frontend/src/main.js`

- [ ] **Step 1: Write evolution.js**

```javascript
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler);

const evolutionInstances = new Map();

export function initEvolutionCharts() {
  document.querySelectorAll("canvas[data-chart='evolution']").forEach((canvas) => {
    const rawData = canvas.dataset.chartData;
    if (!rawData) return;

    if (evolutionInstances.has(canvas)) {
      evolutionInstances.get(canvas).destroy();
    }

    const data = JSON.parse(rawData);

    // Sample data if > 120 points (show every Nth point for readability)
    const step = data.labels.length > 120 ? Math.ceil(data.labels.length / 120) : 1;
    const labels = data.labels.filter((_, i) => i % step === 0);
    const principal = data.principal_series.filter((_, i) => i % step === 0);
    const interest = data.interest_series.filter((_, i) => i % step === 0);
    const balance = data.balance_series.filter((_, i) => i % step === 0);

    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Principal",
            data: principal,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
          },
          {
            label: "Interest",
            data: interest,
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245, 158, 11, 0.1)",
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
          },
          {
            label: "Balance",
            data: balance,
            borderColor: "#6364ed",
            backgroundColor: "rgba(99, 100, 237, 0.05)",
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            ticks: {
              maxTicksLimit: 10,
              color: "#78716c",
              font: { size: 11 },
            },
            grid: { color: "#e7e5e4" },
          },
          y: {
            position: "left",
            title: { display: true, text: "Payment", color: "#78716c", font: { size: 11 } },
            ticks: { color: "#78716c", font: { size: 11 } },
            grid: { color: "#e7e5e4" },
          },
          y1: {
            position: "right",
            title: { display: true, text: "Balance", color: "#78716c", font: { size: 11 } },
            ticks: { color: "#78716c", font: { size: 11 } },
            grid: { drawOnChartArea: false },
          },
        },
        plugins: {
          legend: { position: "bottom", labels: { color: "#1c1917", font: { size: 12 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
            },
          },
        },
      },
    });
    evolutionInstances.set(canvas, chart);
  });
}
```

- [ ] **Step 2: Update main.js to import and init evolution charts**

Add after line 17 in `frontend/src/main.js`:

```javascript
import { initEvolutionCharts } from "./charts/evolution.js";
```

And update the event listeners (lines 19-20):

```javascript
document.addEventListener("DOMContentLoaded", () => { initCharts(); initEvolutionCharts(); });
document.addEventListener("htmx:afterSwap", () => { initCharts(); initEvolutionCharts(); });
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/charts/evolution.js frontend/src/main.js
git commit -m "feat: add evolution line chart module for amortization curves"
```

---

## Chunk 6: Tooltips, Translations & View Tests

### Task 21: Add tooltip texts for new concepts

**Files:**
- Modify: `apps/real_estate/tooltips.py`

- [ ] **Step 1: Add new tooltip entries**

Add to `TERM_TOOLTIPS` dict:

```python
    "monthly_cost": _("Total monthly cost of owning this property: mortgage payment + taxes averaged over 12 months + recurring expenses - rental income if applicable."),
    "net_monthly_cost": _("Your personal share of the monthly cost, based on your ownership percentage or custom payment split."),
    "rate_change": _("When your mortgage term renews, the rate may change. Add rate changes to see how your payments and total interest would be affected."),
    "rental_income": _("Monthly rent received from tenants, minus agency management fees if applicable."),
    "payment_split": _("How each co-owner splits the monthly mortgage payment. By default, based on ownership share. Custom amounts affect long-term equity distribution."),
```

- [ ] **Step 2: Commit**

```bash
git add apps/real_estate/tooltips.py
git commit -m "feat: add tooltip texts for monthly cost, rate changes, rental income, payment split"
```

---

### Task 22: Add view tests for new features

**Files:**
- Modify: `apps/real_estate/tests/test_views.py`

- [ ] **Step 1: Write tests**

Add at the top of the new test code (alongside existing imports):

```python
from apps.real_estate.models import MortgageRateChange, RentalIncome
```

Then add the test classes:

```python
class TestDeleteProperty:
    def test_admin_can_delete(self, client, prop):
        response = client.post(reverse("real_estate:delete", args=[prop.pk]))
        assert response.status_code == 302
        assert not Property.objects.filter(pk=prop.pk).exists()

    def test_confirmation_page(self, client, prop):
        response = client.get(reverse("real_estate:delete", args=[prop.pk]))
        assert response.status_code == 200
        assert b"Delete permanently" in response.content or b"Supprimer" in response.content

    def test_non_owner_gets_404(self, client, user2):
        from apps.real_estate.models import Property

        other_prop = Property.objects.create(
            name="Other", property_type="house", usage="primary",
            address="999 Other St", city="Toronto",
            purchase_price=Decimal("300000"), purchase_date=date(2020, 1, 1),
            current_valuation=Decimal("300000"), valuation_date=date(2024, 1, 1),
        )
        response = client.get(reverse("real_estate:delete", args=[other_prop.pk]))
        assert response.status_code == 404


class TestRateChangeViews:
    def test_add_rate_change(self, client, prop, mortgage):
        response = client.post(
            reverse("real_estate:add_rate_change", args=[prop.pk, mortgage.pk]),
            {"new_annual_rate": "4.500", "effective_date": "2025-06-01", "new_rate_type": "fixed"},
        )
        assert response.status_code == 200
        assert MortgageRateChange.objects.filter(mortgage=mortgage).count() == 1

    def test_delete_rate_change(self, client, prop, mortgage):
        from apps.real_estate.models import MortgageRateChange

        rc = MortgageRateChange.objects.create(
            mortgage=mortgage, new_annual_rate=Decimal("4.000"), effective_date=date(2025, 1, 1),
        )
        response = client.delete(reverse("real_estate:delete_rate_change", args=[prop.pk, mortgage.pk, rc.pk]))
        assert response.status_code == 200
        assert not MortgageRateChange.objects.filter(pk=rc.pk).exists()


class TestRentalIncomeViews:
    def test_add_rental_income(self, client, prop):
        prop.usage = "rental"
        prop.save()
        response = client.post(
            reverse("real_estate:add_rental_income", args=[prop.pk]),
            {"monthly_rent": "1800", "agency_fee_pct": "8", "start_date": "2021-01-01"},
        )
        assert response.status_code == 200
        assert RentalIncome.objects.filter(property=prop).count() == 1


class TestMonthlyCostView:
    def test_monthly_cost_partial(self, client, prop, mortgage):
        response = client.get(reverse("real_estate:monthly_cost", args=[prop.pk]))
        assert response.status_code == 200

    def test_monthly_cost_mine(self, client, prop, mortgage):
        response = client.get(reverse("real_estate:monthly_cost", args=[prop.pk]) + "?mine=1")
        assert response.status_code == 200
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest apps/real_estate/tests/test_views.py -v -k "Delete or RateChange or RentalIncome or MonthlyCost"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/real_estate/tests/test_views.py
git commit -m "test: add view tests for delete, rate changes, rental income, monthly cost"
```

---

### Task 23: Add French translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

- [ ] **Step 1: Add translations for all new strings**

Run `uv run python manage.py makemessages -l fr` to extract new strings, then add translations:

Key translations to add:
```
"Delete" → "Supprimer"
"Delete permanently" → "Supprimer définitivement"
"This action cannot be undone." → "Cette action est irréversible."
"Monthly Cost" → "Coût mensuel"
"Net monthly cost" → "Coût mensuel net"
"Your net monthly cost" → "Votre coût mensuel net"
"Taxes (monthly)" → "Taxes (mensualisées)"
"Recurring expenses" → "Charges récurrentes"
"Rental income (net)" → "Revenu locatif (net)"
"Show my share" → "Voir ma part"
"Show total" → "Voir le total"
"Rate Changes" → "Changements de taux"
"Add rate change" → "Ajouter un changement de taux"
"Delete this rate change?" → "Supprimer ce changement de taux ?"
"No rate changes scheduled." → "Aucun changement de taux prévu."
"Simulation" → "Simulation"
"Rental Income" → "Revenus locatifs"
"Add rental income" → "Ajouter un revenu locatif"
"agency" → "agence"
"from" → "depuis"
"No rental income recorded." → "Aucun revenu locatif enregistré."
"Payment Split" → "Répartition des paiements"
"Set payment split" → "Définir la répartition"
"Amortization Evolution" → "Évolution de l'amortissement"
"View proof" → "Voir le justificatif"
"Monthly cost" → "Coût mensuel"
"mortgage rate change" → "changement de taux hypothécaire"
"rental income" → "revenu locatif"
"owner monthly payment" → "paiement mensuel du copropriétaire"
"proof document link" → "lien vers le justificatif"
"simulation only" → "simulation uniquement"
"new annual rate (%)" → "nouveau taux annuel (%)"
"new rate type" → "nouveau type de taux"
"effective date" → "date d'effet"
"monthly rent" → "loyer mensuel"
"agency fee (%)" → "frais d'agence (%)"
"Percentage taken by rental management agency" → "Pourcentage prélevé par l'agence de gestion locative"
"monthly amount" → "montant mensuel"
"Rental income updated" → "Revenu locatif mis à jour"
"Payment split updated" → "Répartition des paiements mise à jour"
"Property deleted." → "Bien supprimé."
"Your value" → "Votre valeur"
"Your equity" → "Votre équité"
"Your mortgage" → "Votre hypothèque"
```

- [ ] **Step 2: Compile messages**

Run: `uv run python manage.py compilemessages`

- [ ] **Step 3: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for all new real estate features"
```

---

### Task 24: Final integration test — run all tests

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest --cov=apps --cov-report=term-missing -v`
Expected: All tests PASS, no regressions

- [ ] **Step 2: Run linting**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: No issues

- [ ] **Step 3: Run Vite build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Manual smoke test**

Run: `uv run python manage.py runserver` (in one terminal) + `cd frontend && npm run dev` (in another)
Check:
- Property detail page shows monthly cost card
- My-share toggle switches stat card values
- Rate change form works in mortgage section
- Rental income form works for rental properties
- Delete button appears for admin users
- Expense form shows proof link field
- Evolution chart renders below doughnut charts
- All features work in French

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: final integration adjustments"
```
