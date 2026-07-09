# Plan: French Real Estate Support

## Goal

Add support for creating and managing real estate properties in France alongside the existing Canadian system. Reuse the same UI, templates, co-ownership, HTMX patterns, and notification system. Only diverge where French law demands different behavior.

---

## Architecture Decision: Country field, not a separate app

**Approach**: Add a `country` field to `Property` and dispatch country-specific logic in the service layer. No new app, no model inheritance, no template duplication.

**Why**:
- The UI is identical: stat cards, charts, expense/valuation/tax CRUD, sale simulator, co-ownership
- Only 4 things truly differ: mortgage math, tax types, sale simulation (capital gains + fees), and form fields
- A strategy-pattern dispatch in `services.py` keeps it clean without separate apps

```
Property.country = "CA" | "FR"
    → services.py reads property.country → dispatches to correct math
    → forms.py shows/hides fields based on country
    → tooltips.py returns country-appropriate text
```

---

## Phase 1: Model Changes

### 1.1 Add `country` field to Property

```python
# apps/real_estate/models.py

class Property(models.Model):
    COUNTRY_CHOICES = [
        ("CA", _("Canada")),
        ("FR", _("France")),
    ]

    # ... existing fields ...
    country = models.CharField(
        _("country"), max_length=2, choices=COUNTRY_CHOICES, default="CA"
    )
```

**Migration**: Add `country` field with default `"CA"` (all existing properties are Canadian).

### 1.2 Rename `province` to `region` (display-only)

Don't rename the DB column — just update the label dynamically in the form based on country:
- Canada → "Province" (default "QC")
- France → "Departement" (no default)

### 1.3 Rename `welcome_tax_paid` semantics

Same field, different meaning:
- Canada → "Welcome tax" (Quebec mutation tax, ~0.5-1.5% one-time)
- France → "Frais de notaire" (notary fees package, 7-8.5% for ancien)

The field label will be set dynamically in the form. The DB column stays `welcome_tax_paid`.

### 1.4 Update `PropertyTax` types

Add French tax types alongside Canadian ones:

```python
class PropertyTax(models.Model):
    TAX_TYPE_CHOICES = [
        # Canadian
        ("municipal", _("Municipal tax")),
        ("school", _("School tax")),
        # French
        ("taxe_fonciere", _("Taxe foncière")),
        ("taxe_habitation", _("Taxe d'habitation")),
        ("ifi", _("IFI (wealth tax)")),
    ]
```

The unique constraint `(property, tax_type, year)` still works. The form will filter choices by country.

### 1.5 Update `PropertyExpense` types

Add French-specific expense types:

```python
class PropertyExpense(models.Model):
    EXPENSE_TYPE_CHOICES = [
        ("renovation", _("Renovation / Improvement")),
        ("repair", _("Repair / Maintenance")),
        ("property_tax", _("Property tax")),
        ("insurance", _("Insurance")),
        ("condo_fees", _("Condo fees")),
        # French
        ("charges_copro", _("Charges de copropriété")),
        ("assurance_emprunteur", _("Assurance emprunteur")),
        ("other", _("Other")),
    ]
```

### 1.6 Add `Mortgage` fields for French specifics

```python
class Mortgage(models.Model):
    RATE_TYPE_CHOICES = [
        ("fixed", _("Fixed")),
        ("variable", _("Variable")),
        ("mixed", _("Mixed (taux mixte)")),  # NEW: common in France
    ]

    # ... existing fields ...

    # French borrower insurance (assurance emprunteur)
    borrower_insurance_rate = models.DecimalField(
        _("borrower insurance rate (%)"),
        max_digits=5, decimal_places=3, default=0,
        help_text=_("Annual rate for assurance emprunteur (e.g. 0.30)"),
    )
```

**Note**: `insurance_premium` (CMHC, one-time, added to principal) stays for Canada. `borrower_insurance_rate` (annual %, added to monthly payment) is for France. Both default to 0, so no conflict.

### 1.7 Update `CURRENCY_CHOICES` default by country

No model change needed — the form will set the default currency to EUR when country=FR is selected.

### 1.8 Migration file

Single migration:
- Add `country` field (CharField, default="CA")
- Add `borrower_insurance_rate` to Mortgage (default=0)
- Add new choices to `PropertyTax.tax_type` and `PropertyExpense.expense_type`
- Add `"mixed"` to Mortgage `rate_type` choices

```python
# apps/real_estate/migrations/0006_add_france_support.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("real_estate", "0005_add_currency_to_property"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="country",
            field=models.CharField(
                verbose_name="country", max_length=2,
                choices=[("CA", "Canada"), ("FR", "France")],
                default="CA",
            ),
        ),
        migrations.AddField(
            model_name="mortgage",
            name="borrower_insurance_rate",
            field=models.DecimalField(
                verbose_name="borrower insurance rate (%)",
                max_digits=5, decimal_places=3, default=0,
            ),
        ),
        # tax_type and expense_type are CharField choices — no schema change needed,
        # just update the Python choices list. Same for rate_type.
    ]
```

---

## Phase 2: Service Layer — Country-Aware Financial Logic

### 2.1 Mortgage Math: French vs Canadian

The **only** difference is the monthly rate formula:

| | Canada (fixed) | France (all) |
|---|---|---|
| Monthly rate | `(1 + r/2)^(1/6) - 1` | `r / 12` |
| Compounding | Semi-annual (Bank Act) | Monthly proportional |

```python
# apps/real_estate/services.py

def calculate_monthly_rate(annual_rate_pct, rate_type="fixed", country="CA"):
    r = annual_rate_pct / 100
    if country == "FR":
        # France: simple proportional rate, all rate types
        return r / 12
    # Canada: semi-annual compounding for fixed, monthly for variable
    if rate_type == "fixed":
        return (1 + r / 2) ** (Decimal("1") / 6) - 1
    return r / 12


def calculate_monthly_payment(principal, annual_rate_pct, amortization_years,
                               rate_type="fixed", country="CA"):
    r = calculate_monthly_rate(annual_rate_pct, rate_type, country)
    n = amortization_years * 12
    if r == 0:
        return (principal / n).quantize(TWO_PLACES)
    pmt = (r * principal) / (1 - (1 + r) ** (-n))
    return pmt.quantize(TWO_PLACES)
```

### 2.2 Mortgage Model: Monthly Payment with French Insurance

The `Mortgage.monthly_payment` property must account for `borrower_insurance_rate`:

```python
# apps/real_estate/models.py — Mortgage class

@property
def monthly_rate(self):
    r = self.annual_rate / 100
    country = self.real_estate.country
    if country == "FR":
        return r / 12
    if self.rate_type == "fixed":
        return (1 + r / 2) ** (Decimal("1") / 6) - 1
    return r / 12

@property
def monthly_payment(self):
    r = self.monthly_rate
    n = self.amortization_years * 12
    p = self.effective_principal
    if r == 0:
        base = p / n
    else:
        base = (r * p) / (1 - (1 + r) ** (-n))
    # Add French borrower insurance (monthly cost on initial principal)
    insurance_monthly = Decimal("0")
    if self.borrower_insurance_rate:
        insurance_monthly = self.effective_principal * self.borrower_insurance_rate / 100 / 12
    return base + insurance_monthly
```

### 2.3 Amortization Schedule: Pass Country

```python
def generate_amortization_schedule(mortgage):
    country = mortgage.real_estate.country
    r = calculate_monthly_rate(mortgage.annual_rate, mortgage.rate_type, country)
    # ... rest is identical (same payment formula, just different rate)

    # Add insurance line to each payment for French mortgages
    insurance_monthly = Decimal("0")
    if mortgage.borrower_insurance_rate:
        insurance_monthly = (
            mortgage.effective_principal * mortgage.borrower_insurance_rate / 100 / 12
        ).quantize(TWO_PLACES)

    # In each schedule entry, add:
    schedule.append({
        "payment_number": i,
        "date": payment_date,
        "total_payment": actual_payment + insurance_monthly,
        "principal": principal_portion,
        "interest": interest,
        "insurance": insurance_monthly,  # NEW: visible in amortization table
        "balance": balance,
    })
```

### 2.4 Sale Simulation: French Capital Gains Tax

This is the most complex difference. Create a dedicated function:

```python
# apps/real_estate/services.py

def _calculate_french_capital_gains_tax(prop, sale_price):
    """
    French capital gains tax (plus-value immobilière).
    - Primary residence: fully exempt
    - Others: 19% income tax + 17.2% social contributions
    - Progressive abatements by holding period
    - Surtax above €50,000 net gain
    """
    if prop.usage == "primary":
        return Decimal("0"), {}

    acb = _calculate_acb(prop)
    raw_gain = sale_price - acb
    if raw_gain <= 0:
        return Decimal("0"), {}

    # Calculate holding period in full years
    today = date.today()
    holding_years = (today - prop.purchase_date).days // 365

    # Income tax abatement (full exemption after 22 years)
    if holding_years >= 22:
        ir_abatement_pct = Decimal("100")
    elif holding_years <= 5:
        ir_abatement_pct = Decimal("0")
    elif holding_years == 21:
        # Years 6-21: 6% per year = 96%, year 22: +4% = 100%
        ir_abatement_pct = Decimal("96")
    else:
        ir_abatement_pct = Decimal(str((holding_years - 5) * 6))

    # Social contributions abatement (full exemption after 30 years)
    if holding_years >= 30:
        ps_abatement_pct = Decimal("100")
    elif holding_years <= 5:
        ps_abatement_pct = Decimal("0")
    elif holding_years <= 21:
        ps_abatement_pct = Decimal(str((holding_years - 5) * Decimal("1.65")))
    elif holding_years == 22:
        ps_abatement_pct = Decimal("28")
    else:
        ps_abatement_pct = Decimal("28") + Decimal(str((holding_years - 22) * 9))

    ir_taxable = raw_gain * (1 - ir_abatement_pct / 100)
    ps_taxable = raw_gain * (1 - ps_abatement_pct / 100)

    ir_tax = ir_taxable * Decimal("0.19")
    ps_tax = ps_taxable * Decimal("0.172")

    # Surtax on high capital gains (above €50,000 after IR abatement)
    surtax = _calculate_french_surtax(ir_taxable)

    total = (ir_tax + ps_tax + surtax).quantize(TWO_PLACES)
    details = {
        "raw_gain": raw_gain.quantize(TWO_PLACES),
        "holding_years": holding_years,
        "ir_abatement_pct": ir_abatement_pct,
        "ps_abatement_pct": ps_abatement_pct,
        "ir_tax": ir_tax.quantize(TWO_PLACES),
        "ps_tax": ps_tax.quantize(TWO_PLACES),
        "surtax": surtax.quantize(TWO_PLACES),
    }
    return total, details


def _calculate_french_surtax(taxable_gain):
    """Surtax on capital gains above €50,000 (after IR abatement)."""
    pv = taxable_gain
    if pv <= 50000:
        return Decimal("0")
    if pv <= 60000:
        return (pv * Decimal("0.02") - (60000 - pv) * Decimal("0.05")).quantize(TWO_PLACES)
    if pv <= 100000:
        return (pv * Decimal("0.02")).quantize(TWO_PLACES)
    if pv <= 110000:
        return (pv * Decimal("0.03") - (110000 - pv) * Decimal("0.1")).quantize(TWO_PLACES)
    if pv <= 150000:
        return (pv * Decimal("0.03")).quantize(TWO_PLACES)
    if pv <= 160000:
        return (pv * Decimal("0.04") - (160000 - pv) * Decimal("0.15")).quantize(TWO_PLACES)
    if pv <= 200000:
        return (pv * Decimal("0.04")).quantize(TWO_PLACES)
    if pv <= 210000:
        return (pv * Decimal("0.05") - (210000 - pv) * Decimal("0.2")).quantize(TWO_PLACES)
    if pv <= 250000:
        return (pv * Decimal("0.05")).quantize(TWO_PLACES)
    if pv <= 260000:
        return (pv * Decimal("0.06") - (260000 - pv) * Decimal("0.25")).quantize(TWO_PLACES)
    return (pv * Decimal("0.06")).quantize(TWO_PLACES)
```

### 2.5 Sale Simulation: Country-Aware Dispatch

Refactor `estimate_sale_proceeds` to dispatch by country:

```python
def estimate_sale_proceeds(prop, sale_price=None, agent_commission_pct=None, notary_fees=None):
    if sale_price is None:
        sale_price = prop.current_valuation

    # Country-specific defaults
    if prop.country == "FR":
        if agent_commission_pct is None:
            agent_commission_pct = Decimal("5")   # 5% typical in France
        if notary_fees is None:
            notary_fees = Decimal("3000")          # Notary fees at sale (buyer-side, but seller may contribute)
    else:  # CA
        if agent_commission_pct is None:
            agent_commission_pct = Decimal("5")    # 5% typical in Canada
        if notary_fees is None:
            notary_fees = Decimal("800")           # ~$800 notary at sale

    total_mortgage_balance = Decimal("0")
    for mortgage in prop.mortgages.filter(is_active=True):
        total_mortgage_balance += get_remaining_balance(mortgage)

    # Commission
    commission = sale_price * agent_commission_pct / 100
    if prop.country == "CA":
        commission_with_tax = commission * Decimal("1.14975")  # GST + QST
    else:
        commission_with_tax = commission * Decimal("1.20")     # 20% TVA in France

    # Capital gains tax
    capital_gains_details = {}
    if prop.country == "FR":
        capital_gains_tax, capital_gains_details = _calculate_french_capital_gains_tax(prop, sale_price)
    else:
        capital_gains_tax = Decimal("0")
        if prop.usage != "primary":
            acb = _calculate_acb(prop)
            capital_gain = sale_price - acb
            if capital_gain > 0:
                capital_gains_tax = capital_gain * Decimal("0.50") * Decimal("0.45")

    gross_equity = sale_price - total_mortgage_balance
    total_costs = commission_with_tax + notary_fees + capital_gains_tax
    net_proceeds = gross_equity - total_costs

    shares = get_current_ownership_shares(prop)
    per_owner = []
    for ownership, share_pct in shares.items():
        owner_share = net_proceeds * share_pct / 100
        contributions = get_owner_contributions(ownership)
        per_owner.append({
            "user": ownership.user,
            "share_pct": share_pct,
            "net_proceeds": owner_share.quantize(TWO_PLACES),
            "contributions": contributions,
        })

    result = {
        "sale_price": sale_price,
        "mortgage_balance": total_mortgage_balance,
        "gross_equity": gross_equity,
        "agent_commission": commission_with_tax.quantize(TWO_PLACES),
        "notary_fees": notary_fees,
        "capital_gains_tax": capital_gains_tax.quantize(TWO_PLACES),
        "total_costs": total_costs.quantize(TWO_PLACES),
        "net_proceeds": net_proceeds.quantize(TWO_PLACES),
        "per_owner": per_owner,
    }
    if capital_gains_details:
        result["capital_gains_details"] = capital_gains_details
    return result
```

---

## Phase 3: Forms — Country-Aware Fields

### 3.1 Add `country` to PropertyForm

```python
class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "name",
            "country",       # NEW — first field, drives conditional logic
            "property_type",
            "usage",
            "currency",
            "address",
            "city",
            "province",
            "postal_code",
            "purchase_price",
            "purchase_date",
            "welcome_tax_paid",
            "notary_fees_purchase",
            "current_valuation",
            "valuation_date",
            "municipal_assessment",
        ]
        widgets = {
            # ... existing widgets ...
            "country": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
        }
```

### 3.2 Dynamic Field Labels by Country

Override labels in `__init__` based on initial/data country value:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # ... existing date/tooltip logic ...

    country = self._get_country(args, kwargs)
    if country == "FR":
        self.fields["province"].label = _("Département")
        self.fields["province"].initial = ""
        self.fields["welcome_tax_paid"].label = _("Frais de notaire (achat)")
        self.fields["welcome_tax_paid"].help_text = _(
            "The total 'frais de notaire' paid at purchase (typically 7-8.5% for "
            "existing properties, 2-3% for new builds). Includes transfer taxes, "
            "notary fees, and disbursements."
        )
        self.fields["notary_fees_purchase"].label = _("Frais d'agence (achat)")
        self.fields["notary_fees_purchase"].help_text = _(
            "Real estate agent fees paid at purchase, if any."
        )
        self.fields["municipal_assessment"].label = _("Valeur cadastrale")
        self.fields["municipal_assessment"].help_text = _(
            "The cadastral rental value used to calculate taxe foncière. "
            "Found on your taxe foncière notice."
        )
        self.fields["currency"].initial = "EUR"

def _get_country(self, args, kwargs):
    """Extract country from form data or instance."""
    if self.instance and self.instance.pk:
        return self.instance.country
    if self.data:
        return self.data.get("country", "CA")
    return self.initial.get("country", "CA")
```

### 3.3 MortgageForm: French Fields

```python
class MortgageForm(forms.ModelForm):
    class Meta:
        model = Mortgage
        fields = [
            "lender",
            "principal",
            "annual_rate",
            "rate_type",
            "amortization_years",
            "term_years",
            "payment_frequency",
            "start_date",
            "insurance_premium",
            "borrower_insurance_rate",  # NEW
        ]
        widgets = {
            # ... existing widgets ...
            "borrower_insurance_rate": forms.NumberInput(
                attrs={"class": TAILWIND_INPUT_CLASS, "step": "0.001"}
            ),
        }

    def __init__(self, *args, country="CA", **kwargs):
        super().__init__(*args, **kwargs)
        # ... existing logic ...
        self.country = country

        if country == "FR":
            # Hide Canadian-specific fields
            self.fields["insurance_premium"].widget = forms.HiddenInput()
            self.fields["term_years"].widget = forms.HiddenInput()
            # Relabel
            self.fields["amortization_years"].label = _("Loan duration (years)")
            self.fields["amortization_years"].help_text = _(
                "Total mortgage duration. Common in France: 15, 20, or 25 years. "
                "Maximum allowed: 25 years (27 for new construction with deferred start)."
            )
            self.fields["borrower_insurance_rate"].help_text = _(
                "Annual rate for assurance emprunteur (e.g. 0.30 for 0.30%). "
                "Required by all French banks. Typical rates: 0.15-0.50% depending on age."
            )
        else:
            # Hide French fields for Canadian properties
            self.fields["borrower_insurance_rate"].widget = forms.HiddenInput()
```

### 3.4 PropertyTaxForm: Filter Choices by Country

```python
class PropertyTaxForm(forms.ModelForm):
    CA_TAX_TYPES = [("municipal", _("Municipal tax")), ("school", _("School tax"))]
    FR_TAX_TYPES = [
        ("taxe_fonciere", _("Taxe foncière")),
        ("taxe_habitation", _("Taxe d'habitation")),
        ("ifi", _("IFI (wealth tax)")),
    ]

    def __init__(self, *args, country="CA", **kwargs):
        super().__init__(*args, **kwargs)
        if country == "FR":
            self.fields["tax_type"].choices = self.FR_TAX_TYPES
        else:
            self.fields["tax_type"].choices = self.CA_TAX_TYPES
```

---

## Phase 4: Views — Minimal Changes

### 4.1 Property Create: Pass Country to Forms

```python
# apps/real_estate/views.py — property_create

@login_required
def property_create(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        country = request.POST.get("country", "CA")
        mortgage_form = MortgageForm(request.POST, prefix="mortgage", country=country)
        if form.is_valid() and mortgage_form.is_valid():
            prop = form.save()
            # ... rest unchanged ...
    else:
        form = PropertyForm()
        mortgage_form = MortgageForm(prefix="mortgage")
    return render(request, "real_estate/create.html", {
        "form": form,
        "mortgage_form": mortgage_form,
    })
```

### 4.2 Property Detail: Pass Country to Tax/Sale Logic

```python
# In property_detail view — when building sale estimate:
# No change needed — estimate_sale_proceeds already reads prop.country

# When adding taxes — pass country to form:
# This is done in add_tax, edit_tax views
```

### 4.3 Tax/Expense Views: Pass Country to Forms

```python
@login_required
def add_tax(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    if request.method == "POST":
        form = PropertyTaxForm(request.POST, country=prop.country)
        # ... rest unchanged ...
    else:
        form = PropertyTaxForm(country=prop.country)
    # ... rest unchanged ...
```

Same pattern for `edit_tax`.

### 4.4 Sale Simulator: Pass Commission Default

```python
@login_required
def sale_simulator(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    sale_price = request.GET.get("sale_price")
    commission = request.GET.get("commission")
    # ... parse values ...
    estimate = estimate_sale_proceeds(
        prop,
        sale_price=Decimal(sale_price) if sale_price else None,
        agent_commission_pct=Decimal(commission) if commission else None,
    )
    return render(request, "real_estate/partials/sale_estimate.html", {
        "estimate": estimate,
        "property": prop,
    })
```

---

## Phase 5: Templates — Country-Aware Display

### 5.1 Create Form: Country Selector with Dynamic UI

In `create.html`, add Alpine.js reactivity to the country selector:

```html
<!-- In create.html, wrap form in Alpine component -->
<form method="post" x-data="propertyForm()">
  {% csrf_token %}

  {% include "components/card_start.html" with title=_("Property details") %}
    <div class="grid gap-4 sm:grid-cols-2">
      <!-- Country selector — first field -->
      <div>
        <label for="{{ form.country.id_for_label }}" class="block text-sm font-medium text-text mb-1">
          {{ form.country.label }}<span class="text-danger-600 ml-0.5">*</span>
        </label>
        {{ form.country }}
      </div>

      <!-- Loop other fields, conditionally show/hide based on country -->
      {% for field in form %}
        {% if field.name == "province" %}
        <div x-show="country === 'CA'">
          <!-- Province (Canada) -->
          <label>{% trans "Province" %}</label>
          {{ field }}
        </div>
        <div x-show="country === 'FR'">
          <!-- Département (France) -->
          <label>{% trans "Département" %}</label>
          {{ field }}
        </div>
        {% endif %}

        {% if field.name == "welcome_tax_paid" %}
        <div>
          <label x-text="country === 'FR' ? '{% trans "Frais de notaire (achat)" %}' : '{% trans "Welcome tax paid" %}'">
          </label>
          {{ field }}
        </div>
        {% endif %}
      {% endfor %}
    </div>
  {% include "components/card_end.html" %}

  <!-- Mortgage: show/hide fields based on country -->
  {% include "components/card_start.html" with title=_("Mortgage (optional)") %}
    <div class="grid gap-4 sm:grid-cols-2">
      {% for field in mortgage_form %}
        <!-- Hide CMHC insurance for France -->
        {% if field.name == "insurance_premium" %}
        <div x-show="country === 'CA'">
        {% elif field.name == "term_years" %}
        <div x-show="country === 'CA'">
        {% elif field.name == "borrower_insurance_rate" %}
        <div x-show="country === 'FR'">
        {% else %}
        <div>
        {% endif %}
          <label>{{ field.label }}</label>
          {{ field }}
        </div>
      {% endfor %}
    </div>
  {% include "components/card_end.html" %}
</form>

<script>
function propertyForm() {
  return {
    country: document.getElementById('id_country')?.value || 'CA',
    init() {
      const countrySelect = document.getElementById('id_country');
      if (countrySelect) {
        this.$watch('country', (val) => {
          // Update currency default
          const currencySelect = document.getElementById('id_currency');
          if (currencySelect && !currencySelect._dirty) {
            currencySelect.value = val === 'FR' ? 'EUR' : 'CAD';
          }
          // Update province default
          const province = document.getElementById('id_province');
          if (province && !province._dirty) {
            province.value = val === 'FR' ? '' : 'QC';
          }
        });
        countrySelect.addEventListener('change', (e) => {
          this.country = e.target.value;
        });
      }
    }
  };
}
</script>
```

### 5.2 Detail Page: French Sale Estimate Details

In `sale_estimate.html`, add optional French capital gains breakdown:

```html
<!-- After capital gains tax row, show French details if available -->
{% if estimate.capital_gains_details %}
  <div class="ml-4 space-y-1 text-xs text-text-muted border-l-2 border-border pl-3 my-2">
    <div class="flex justify-between">
      <span>{% trans "Holding period" %}</span>
      <span>{{ estimate.capital_gains_details.holding_years }} {% trans "years" %}</span>
    </div>
    <div class="flex justify-between">
      <span>{% trans "Income tax (19%)" %}</span>
      <span class="font-mono">{% show_money estimate.capital_gains_details.ir_tax property.currency %}</span>
    </div>
    <div class="flex justify-between">
      <span>{% trans "Social contributions (17.2%)" %}</span>
      <span class="font-mono">{% show_money estimate.capital_gains_details.ps_tax property.currency %}</span>
    </div>
    {% if estimate.capital_gains_details.surtax > 0 %}
    <div class="flex justify-between">
      <span>{% trans "Surtax" %}</span>
      <span class="font-mono">{% show_money estimate.capital_gains_details.surtax property.currency %}</span>
    </div>
    {% endif %}
    <div class="flex justify-between">
      <span>{% trans "IR abatement" %}</span>
      <span>{{ estimate.capital_gains_details.ir_abatement_pct }}%</span>
    </div>
    <div class="flex justify-between">
      <span>{% trans "Social abatement" %}</span>
      <span>{{ estimate.capital_gains_details.ps_abatement_pct }}%</span>
    </div>
  </div>
{% endif %}
```

### 5.3 Detail Page: Commission Label

In `detail.html`, the sale simulator commission default should change:

```html
<input type="number"
       value="{% if property.country == 'FR' %}5{% else %}5{% endif %}"
       step="0.5" min="0" max="10"
       class="input"
       name="commission" />
```

(Same default, but the label context changes — could add a tooltip explaining French vs Canadian commission norms.)

### 5.4 Amortization Table: Insurance Column for France

In `amortization.html`, conditionally show insurance column:

```html
<thead>
  <tr>
    <th>#</th>
    <th>{% trans "Date" %}</th>
    <th>{% trans "Payment" %}</th>
    <th>{% trans "Principal" %}</th>
    <th>{% trans "Interest" %}</th>
    {% if property.country == "FR" and mortgage.borrower_insurance_rate %}
    <th>{% trans "Insurance" %}</th>
    {% endif %}
    <th>{% trans "Balance" %}</th>
  </tr>
</thead>
<tbody>
  {% for entry in schedule %}
  <tr>
    <td>{{ entry.payment_number }}</td>
    <td>{{ entry.date|date:"M Y" }}</td>
    <td>{% show_money entry.total_payment property.currency %}</td>
    <td>{% show_money entry.principal property.currency %}</td>
    <td>{% show_money entry.interest property.currency %}</td>
    {% if property.country == "FR" and mortgage.borrower_insurance_rate %}
    <td>{% show_money entry.insurance property.currency %}</td>
    {% endif %}
    <td>{% show_money entry.balance property.currency %}</td>
  </tr>
  {% endfor %}
</tbody>
```

### 5.5 Detail Page: Tax Section Label

In `detail.html`, the tax card title should be country-aware:

```html
{% if property.country == "FR" %}
  {% include "components/card_start.html" with title=_("Taxes & Charges") %}
{% else %}
  {% include "components/card_start.html" with title=_("Property Taxes") %}
{% endif %}
```

---

## Phase 6: Tooltips — Country-Aware Educational Content

### 6.1 Split Tooltips by Country

```python
# apps/real_estate/tooltips.py

TERM_TOOLTIPS_CA = {
    "amortization": _(
        "The total number of years to fully pay off the mortgage. "
        "In Canada, 25 years is the most common amortization period."
    ),
    "agent_commission": _(
        "The real estate agent's fee, typically 4-6% of the sale price in Canada. "
        "This includes applicable sales taxes (GST/QST)."
    ),
    "capital_gains_tax": _(
        "If this isn't your primary residence, you may owe tax on the profit. "
        "In Canada, 50% of the capital gain is taxable at your marginal rate."
    ),
    "insurance_premium": _(
        "If your down payment was less than 20%, you likely paid CMHC/Sagen/Canada Guaranty "
        "insurance. This premium is usually added to the mortgage principal."
    ),
}

TERM_TOOLTIPS_FR = {
    "amortization": _(
        "The total duration of your mortgage in years. "
        "In France, 20 or 25 years is most common. Maximum allowed: 25 years."
    ),
    "agent_commission": _(
        "The real estate agent's fee, typically 3-6% of the sale price in France. "
        "This includes 20% TVA."
    ),
    "capital_gains_tax": _(
        "If this isn't your primary residence, you owe plus-value tax on the profit: "
        "19% income tax + 17.2% social contributions. Abatements apply based on how long "
        "you've owned the property — full IR exemption after 22 years, full social exemption after 30."
    ),
    "borrower_insurance_rate": _(
        "Assurance emprunteur — mandatory insurance covering death, disability, and job loss. "
        "Paid monthly on top of your mortgage payment. Typical rate: 0.15-0.50% per year of the loan amount."
    ),
    "frais_notaire": _(
        "The 'frais de notaire' include transfer taxes (droits de mutation), notary fees, "
        "and administrative costs. For existing properties: 7-8.5% of the price. "
        "For new builds: 2-3% (VAT is included in the purchase price instead)."
    ),
    "taxe_fonciere": _(
        "Annual property tax paid to the municipality. Based on the cadastral value "
        "and local tax rates. Varies widely by location."
    ),
    "taxe_habitation": _(
        "Abolished for all primary residences since 2023. Still applies to "
        "secondary residences, with possible surcharges in high-demand areas."
    ),
    "ifi": _(
        "Wealth tax on real estate (Impôt sur la Fortune Immobilière). "
        "Applies if your total net real estate exceeds €1,300,000. "
        "Primary residence benefits from a 30% valuation abatement."
    ),
}

# Base tooltips (country-agnostic) stay in TERM_TOOLTIPS
# Country-specific ones override via:
def get_tooltips(country="CA"):
    tips = dict(TERM_TOOLTIPS)  # Start with base
    if country == "FR":
        tips.update(TERM_TOOLTIPS_FR)
    else:
        tips.update(TERM_TOOLTIPS_CA)
    return tips
```

### 6.2 Update Views to Use Country-Aware Tooltips

```python
# apps/real_estate/views.py — property_detail

from .tooltips import get_tooltips

@login_required
def property_detail(request, pk):
    # ...
    tips = get_tooltips(prop.country)
    return render(request, "real_estate/detail.html", {
        # ...
        "tips": tips,
    })
```

---

## Phase 7: Form Field Tooltips — Country-Aware

### 7.1 Update FIELD_TOOLTIPS

```python
# apps/real_estate/forms.py

FIELD_TOOLTIPS_CA = {
    "welcome_tax_paid": _(
        "Also called 'mutation tax'. A one-time tax paid to the municipality "
        "when you buy a property. Your notary should have the exact amount."
    ),
    "insurance_premium": _(
        "If your down payment was less than 20%, you likely paid CMHC/Sagen/Canada Guaranty "
        "insurance. This premium is usually added to the mortgage principal."
    ),
    "amortization_years": _(
        "Total number of years to fully pay off the mortgage. Most common in Canada: 25 years."
    ),
    "term_years": _(
        "The length of your current mortgage contract before renewal. Most common in Canada: 5 years."
    ),
    "municipal_assessment": _(
        "The value assigned by your municipality for property tax purposes. Found on your municipal tax bill."
    ),
}

FIELD_TOOLTIPS_FR = {
    "welcome_tax_paid": _(
        "Total 'frais de notaire' paid at purchase. Includes transfer taxes (droits de mutation), "
        "notary fees, and administrative costs. Typically 7-8.5% for existing properties, "
        "2-3% for new builds."
    ),
    "borrower_insurance_rate": _(
        "Annual rate for assurance emprunteur (e.g. 0.30 for 0.30%). "
        "Required by all French banks. Typical rates: 0.15-0.50% depending on age."
    ),
    "amortization_years": _(
        "Total mortgage duration in years. Most common in France: 20 or 25 years. "
        "Maximum allowed by regulation: 25 years."
    ),
    "municipal_assessment": _(
        "The cadastral rental value (valeur locative cadastrale) used to calculate taxe foncière. "
        "Found on your taxe foncière notice."
    ),
}

def _apply_tooltips(form, country="CA"):
    """Set help_text on form fields from FIELD_TOOLTIPS."""
    # Apply base tooltips
    for field_name, tooltip in FIELD_TOOLTIPS.items():
        if field_name in form.fields:
            form.fields[field_name].help_text = tooltip
    # Override with country-specific
    overrides = FIELD_TOOLTIPS_FR if country == "FR" else FIELD_TOOLTIPS_CA
    for field_name, tooltip in overrides.items():
        if field_name in form.fields:
            form.fields[field_name].help_text = tooltip
```

---

## Phase 8: JavaScript — Country-Aware Auto-Calculations

### 8.1 Remove CMHC Logic for France

In `create.html` script, the CMHC insurance calculation should only run for Canada:

```javascript
function updateInsurance() {
  if (insuranceDirty || !insurancePremium) return;
  // Only auto-calculate CMHC for Canadian properties
  const country = document.getElementById('id_country')?.value || 'CA';
  if (country !== 'CA') {
    insurancePremium.value = '0.00';
    return;
  }
  // ... existing CMHC logic ...
}
```

### 8.2 French Frais de Notaire Auto-Calculation (Optional Nice-to-Have)

Could auto-estimate frais de notaire when country=FR based on purchase price:

```javascript
function updateFraisNotaire() {
  const country = document.getElementById('id_country')?.value;
  if (country !== 'FR') return;
  const welcomeTax = document.getElementById('id_welcome_tax_paid');
  if (!welcomeTax || welcomeTax._dirty) return;
  const price = parseFloat(purchasePrice?.value) || 0;
  if (price > 0) {
    // ~8% for existing properties (rough estimate)
    welcomeTax.value = (price * 0.08).toFixed(2);
  }
}
```

---

## Phase 9: Exchange Rates — Add EUR as Base Currency

### 9.1 Update Fallback Rates

The existing `exchange_rates.py` already supports EUR. No changes needed — it fetches from `open.er-api.com/v6/latest/CAD` and supports CAD↔EUR conversion.

If we want to add more currencies later (GBP, USD), we just expand `FALLBACK_RATES` and `CURRENCY_SYMBOLS`.

---

## Phase 10: Tests

### 10.1 French Mortgage Math Tests

```python
# apps/real_estate/tests/test_services.py

class TestFrenchMonthlyRate:
    def test_fixed_rate_uses_simple_division(self):
        """France uses r/12 for all rate types, no semi-annual compounding."""
        rate = calculate_monthly_rate(Decimal("3.5"), rate_type="fixed", country="FR")
        expected = Decimal("3.5") / 100 / 12
        assert abs(rate - expected) < Decimal("0.000001")

    def test_variable_rate_same_as_fixed(self):
        """France: variable and fixed use same monthly rate formula."""
        fixed = calculate_monthly_rate(Decimal("3.5"), rate_type="fixed", country="FR")
        variable = calculate_monthly_rate(Decimal("3.5"), rate_type="variable", country="FR")
        assert fixed == variable

    def test_french_rate_higher_than_canadian(self):
        """At same nominal rate, French monthly rate is slightly higher than Canadian."""
        fr_rate = calculate_monthly_rate(Decimal("5.0"), rate_type="fixed", country="FR")
        ca_rate = calculate_monthly_rate(Decimal("5.0"), rate_type="fixed", country="CA")
        assert fr_rate > ca_rate


class TestFrenchMonthlyPayment:
    def test_standard_french_mortgage(self):
        """200k EUR at 3.5% over 20 years."""
        pmt = calculate_monthly_payment(
            Decimal("200000"), Decimal("3.5"), 20,
            rate_type="fixed", country="FR",
        )
        # Expected: ~1,159.92 EUR/month
        assert Decimal("1155") < pmt < Decimal("1165")

    def test_french_with_borrower_insurance(self):
        """Payment + insurance = total monthly cost."""
        base_pmt = calculate_monthly_payment(
            Decimal("200000"), Decimal("3.5"), 20,
            rate_type="fixed", country="FR",
        )
        insurance_monthly = Decimal("200000") * Decimal("0.30") / 100 / 12  # 0.30% annual
        total = base_pmt + insurance_monthly
        assert total > base_pmt
        assert insurance_monthly == Decimal("50.00")
```

### 10.2 French Capital Gains Tax Tests

```python
class TestFrenchCapitalGainsTax:
    @pytest.fixture
    def french_rental(self, user):
        prop = Property.objects.create(
            name="Paris Apartment", property_type="condo", usage="rental",
            address="10 Rue de Rivoli", city="Paris",
            province="75", country="FR", currency="EUR",
            purchase_price=300000, purchase_date=date(2015, 1, 1),
            current_valuation=400000, valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        return prop

    def test_primary_residence_exempt(self, user):
        prop = Property.objects.create(
            name="Paris Home", property_type="condo", usage="primary",
            address="5 Av Montaigne", city="Paris",
            province="75", country="FR", currency="EUR",
            purchase_price=500000, purchase_date=date(2010, 1, 1),
            current_valuation=800000, valuation_date=date(2026, 1, 1),
        )
        tax, details = _calculate_french_capital_gains_tax(prop, Decimal("800000"))
        assert tax == Decimal("0")

    def test_rental_under_5_years_no_abatement(self, french_rental):
        """Property held < 5 years: no abatement, full tax."""
        french_rental.purchase_date = date(2024, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        # Gain: 100k. IR: 19% of 100k = 19,000. PS: 17.2% of 100k = 17,200
        assert details["ir_abatement_pct"] == Decimal("0")
        assert details["ps_abatement_pct"] == Decimal("0")
        assert details["ir_tax"] == Decimal("19000.00")
        assert details["ps_tax"] == Decimal("17200.00")

    def test_rental_10_years_partial_abatement(self, french_rental):
        """Property held 10 years: 30% IR abatement, 8.25% PS abatement."""
        french_rental.purchase_date = date(2016, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        assert details["holding_years"] == 10
        assert details["ir_abatement_pct"] == Decimal("30")  # (10-5)*6%
        assert abs(details["ps_abatement_pct"] - Decimal("8.25")) < Decimal("0.01")  # (10-5)*1.65%

    def test_rental_22_years_ir_exempt(self, french_rental):
        """Property held 22+ years: full IR exemption, partial PS."""
        french_rental.purchase_date = date(2004, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        assert details["ir_abatement_pct"] == Decimal("100")
        assert details["ir_tax"] == Decimal("0")
        assert details["ps_tax"] > 0  # Still partial PS

    def test_rental_30_years_fully_exempt(self, french_rental):
        """Property held 30+ years: fully exempt from all taxes."""
        french_rental.purchase_date = date(1995, 1, 1)
        french_rental.save()
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("400000"))
        assert tax == Decimal("0")

    def test_no_gain_no_tax(self, french_rental):
        """No capital gain = no tax."""
        tax, details = _calculate_french_capital_gains_tax(french_rental, Decimal("250000"))
        assert tax == Decimal("0")


class TestFrenchSurtax:
    def test_no_surtax_under_50k(self):
        assert _calculate_french_surtax(Decimal("49000")) == Decimal("0")

    def test_surtax_at_100k(self):
        result = _calculate_french_surtax(Decimal("100000"))
        assert result == Decimal("2000.00")  # 2% * 100k

    def test_surtax_at_260k_plus(self):
        result = _calculate_french_surtax(Decimal("300000"))
        assert result == Decimal("18000.00")  # 6% * 300k
```

### 10.3 French Sale Simulation Tests

```python
class TestFrenchSaleSimulation:
    def test_french_commission_includes_tva(self, user):
        """French commission includes 20% TVA (not 14.975% GST+QST)."""
        prop = Property.objects.create(
            name="Lyon House", property_type="house", usage="primary",
            address="1 Place Bellecour", city="Lyon",
            province="69", country="FR", currency="EUR",
            purchase_price=400000, purchase_date=date(2020, 1, 1),
            current_valuation=500000, valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        estimate = estimate_sale_proceeds(prop, sale_price=Decimal("500000"))
        # Commission: 5% * 500k = 25k * 1.20 TVA = 30k
        assert estimate["agent_commission"] == Decimal("30000.00")

    def test_french_primary_no_cgt(self, user):
        """Primary residence in France: no capital gains tax."""
        prop = Property.objects.create(
            name="Paris Home", property_type="condo", usage="primary",
            address="5 Rue de Passy", city="Paris",
            province="75", country="FR", currency="EUR",
            purchase_price=500000, purchase_date=date(2015, 1, 1),
            current_valuation=700000, valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        estimate = estimate_sale_proceeds(prop, sale_price=Decimal("700000"))
        assert estimate["capital_gains_tax"] == Decimal("0.00")

    def test_french_rental_has_cgt(self, user):
        """Rental in France: capital gains tax applies."""
        prop = Property.objects.create(
            name="Nice Studio", property_type="condo", usage="rental",
            address="10 Prom. des Anglais", city="Nice",
            province="06", country="FR", currency="EUR",
            purchase_price=200000, purchase_date=date(2022, 1, 1),
            current_valuation=250000, valuation_date=date(2026, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        estimate = estimate_sale_proceeds(prop, sale_price=Decimal("250000"))
        assert estimate["capital_gains_tax"] > Decimal("0")
        assert "capital_gains_details" in estimate
```

### 10.4 French View Tests

```python
class TestCreateFrenchProperty:
    @pytest.fixture(autouse=True)
    def setup(self, client, user):
        client.force_login(user)

    def test_create_french_property(self, client):
        response = client.post("/real-estate/create/", {
            "name": "Appartement Paris",
            "country": "FR",
            "property_type": "condo",
            "usage": "primary",
            "currency": "EUR",
            "address": "10 Rue de Rivoli",
            "city": "Paris",
            "province": "75",
            "purchase_price": "300000",
            "purchase_date": "2024-01-15",
            "welcome_tax_paid": "24000",   # ~8% frais de notaire
            "notary_fees_purchase": "0",
            "current_valuation": "320000",
            "valuation_date": "2026-01-01",
            "down_payment": "60000",
        })
        assert response.status_code == 302
        prop = Property.objects.get(name="Appartement Paris")
        assert prop.country == "FR"
        assert prop.currency == "EUR"

    def test_french_property_with_mortgage(self, client):
        response = client.post("/real-estate/create/", {
            "name": "Maison Lyon",
            "country": "FR",
            "property_type": "house",
            "usage": "primary",
            "currency": "EUR",
            "address": "5 Place Bellecour",
            "city": "Lyon",
            "province": "69",
            "purchase_price": "400000",
            "purchase_date": "2024-06-01",
            "welcome_tax_paid": "32000",
            "notary_fees_purchase": "0",
            "current_valuation": "420000",
            "valuation_date": "2026-01-01",
            "down_payment": "80000",
            "mortgage-lender": "BNP Paribas",
            "mortgage-principal": "320000",
            "mortgage-annual_rate": "3.500",
            "mortgage-rate_type": "fixed",
            "mortgage-amortization_years": "20",
            "mortgage-start_date": "2024-07-01",
            "mortgage-borrower_insurance_rate": "0.300",
        })
        assert response.status_code == 302
        prop = Property.objects.get(name="Maison Lyon")
        mortgage = prop.mortgages.first()
        assert mortgage.borrower_insurance_rate == Decimal("0.300")
        assert mortgage.insurance_premium == 0  # No CMHC for France

    def test_french_tax_types(self, client, user):
        """French property shows French tax types."""
        prop = Property.objects.create(
            name="Test FR", property_type="condo", usage="primary",
            address="1 Rue", city="Paris", province="75",
            country="FR", currency="EUR",
            purchase_price=300000, purchase_date=date(2024, 1, 1),
            current_valuation=300000, valuation_date=date(2024, 1, 1),
        )
        PropertyOwnership.objects.create(user=user, property=prop, is_admin=True)
        response = client.post(f"/real-estate/{prop.pk}/tax/", {
            "tax_type": "taxe_fonciere",
            "year": "2025",
            "amount": "1500",
        })
        assert response.status_code == 200
        assert PropertyTax.objects.filter(
            property=prop, tax_type="taxe_fonciere"
        ).exists()
```

---

## Phase 11: Translations

### 11.1 New Translation Strings

Add to `locale/fr/LC_MESSAGES/django.po`:

```po
# Country
msgid "Canada"
msgstr "Canada"

msgid "France"
msgstr "France"

# French tax types
msgid "Taxe foncière"
msgstr "Taxe foncière"

msgid "Taxe d'habitation"
msgstr "Taxe d'habitation"

msgid "IFI (wealth tax)"
msgstr "IFI (impôt sur la fortune immobilière)"

# French mortgage
msgid "Mixed (taux mixte)"
msgstr "Mixte (taux mixte)"

msgid "borrower insurance rate (%)"
msgstr "taux d'assurance emprunteur (%)"

msgid "Loan duration (years)"
msgstr "Durée du prêt (années)"

# French form labels
msgid "Département"
msgstr "Département"

msgid "Frais de notaire (achat)"
msgstr "Frais de notaire (achat)"

msgid "Frais d'agence (achat)"
msgstr "Frais d'agence (achat)"

msgid "Valeur cadastrale"
msgstr "Valeur cadastrale"

# French expense types
msgid "Charges de copropriété"
msgstr "Charges de copropriété"

msgid "Assurance emprunteur"
msgstr "Assurance emprunteur"

# French sale simulation
msgid "Holding period"
msgstr "Durée de détention"

msgid "Income tax (19%)"
msgstr "Impôt sur le revenu (19 %)"

msgid "Social contributions (17.2%)"
msgstr "Prélèvements sociaux (17,2 %)"

msgid "Surtax"
msgstr "Surtaxe"

msgid "IR abatement"
msgstr "Abattement IR"

msgid "Social abatement"
msgstr "Abattement prélèvements sociaux"

# French tooltips
msgid "Taxes & Charges"
msgstr "Impôts et charges"
```

---

## Summary: Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `apps/real_estate/models.py` | Modify | Add `country` to Property, `borrower_insurance_rate` to Mortgage, new tax/expense types, `"mixed"` rate type |
| `apps/real_estate/migrations/0006_*.py` | Create | Migration for new fields |
| `apps/real_estate/services.py` | Modify | Add `country` param to mortgage math, add `_calculate_french_capital_gains_tax`, `_calculate_french_surtax`, update `estimate_sale_proceeds` |
| `apps/real_estate/forms.py` | Modify | Add `country` to PropertyForm, dynamic labels, country-aware MortgageForm/PropertyTaxForm |
| `apps/real_estate/tooltips.py` | Modify | Add `TERM_TOOLTIPS_FR`, `TERM_TOOLTIPS_CA`, `get_tooltips()` function |
| `apps/real_estate/views.py` | Modify | Pass `country` to forms, use `get_tooltips(country)` |
| `templates/real_estate/create.html` | Modify | Alpine.js country switcher, conditional field display |
| `templates/real_estate/detail.html` | Modify | Country-aware tax card title |
| `templates/real_estate/partials/sale_estimate.html` | Modify | French capital gains breakdown |
| `templates/real_estate/amortization.html` | Modify | Optional insurance column |
| `apps/real_estate/tests/test_services.py` | Modify | French mortgage math + capital gains + surtax tests |
| `apps/real_estate/tests/test_views.py` | Modify | French property creation + tax tests |
| `locale/fr/LC_MESSAGES/django.po` | Modify | New French translation strings |

**Estimated new/modified lines**: ~500 in services, ~100 in models, ~150 in forms, ~100 in templates, ~200 in tests = ~1,050 total

**What stays 100% unchanged**:
- Co-ownership system (OwnershipPeriod, shares, invitations)
- Notification system
- HTMX expense/valuation/tax CRUD patterns
- Template layout and design system components
- Exchange rate system
- All existing Canadian tests (backwards compatible)

---

## TODO List

### Phase 1: Model Changes ✅
- [x] **1.1** Add `COUNTRY_CHOICES` and `country` CharField to `Property` model (default `"CA"`)
- [x] **1.2** Add `"mixed"` to `Mortgage.RATE_TYPE_CHOICES`
- [x] **1.3** Add `borrower_insurance_rate` DecimalField to `Mortgage` model (default 0)
- [x] **1.4** Add French tax types to `PropertyTax.TAX_TYPE_CHOICES`: `taxe_fonciere`, `taxe_habitation`, `ifi`
- [x] **1.5** Add French expense types to `PropertyExpense.EXPENSE_TYPE_CHOICES`: `charges_copro`, `assurance_emprunteur`
- [x] **1.6** Create migration `0006_add_france_support.py` (AddField country, AddField borrower_insurance_rate)
- [x] **1.7** Run migration and verify no breakage on existing Canadian properties
- [x] **1.8** Run existing test suite — all 139+ tests must still pass (backwards compatible)

### Phase 2: Service Layer — Country-Aware Financial Logic ✅
- [x] **2.1** Add `country` parameter to `calculate_monthly_rate()` — dispatch `r/12` for FR, keep semi-annual for CA
- [x] **2.2** Add `country` parameter to `calculate_monthly_payment()` — pass through to `calculate_monthly_rate()`
- [x] **2.3** Update `Mortgage.monthly_rate` property to read `self.real_estate.country` and dispatch accordingly
- [x] **2.4** Update `Mortgage.monthly_payment` property to add `borrower_insurance_rate` monthly cost on top of base payment
- [x] **2.5** Update `generate_amortization_schedule()` to pass country to rate calculation
- [x] **2.6** Add `insurance` key to each amortization schedule entry (0 for CA, calculated for FR)
- [x] **2.7** Implement `_calculate_french_capital_gains_tax(prop, sale_price)` — IR abatement table, PS abatement table, holding period
- [x] **2.8** Implement `_calculate_french_surtax(taxable_gain)` — 11-bracket surtax on gains above €50k
- [x] **2.9** Refactor `estimate_sale_proceeds()` — make `agent_commission_pct` and `notary_fees` default to `None`, set country-specific defaults inside function
- [x] **2.10** Update commission tax in `estimate_sale_proceeds()` — 20% TVA for FR vs 14.975% GST+QST for CA
- [x] **2.11** Update capital gains dispatch in `estimate_sale_proceeds()` — call `_calculate_french_capital_gains_tax` for FR, keep existing logic for CA
- [x] **2.12** Add `capital_gains_details` dict to sale estimate result when FR (holding years, IR/PS breakdown, abatements, surtax)
- [x] **2.13** Verify existing Canadian tests still pass after all service changes

### Phase 3: Forms — Country-Aware Fields ✅
- [x] **3.1** Add `"country"` to `PropertyForm.Meta.fields` list (position it early, before property_type)
- [x] **3.2** Add `"country"` widget to `PropertyForm.Meta.widgets` (Select with Tailwind class)
- [x] **3.3** Add `_get_country()` helper method to `PropertyForm` (reads from instance, data, or initial)
- [x] **3.4** Add country-aware label overrides in `PropertyForm.__init__()` — province→Département, welcome_tax→Frais de notaire, etc.
- [x] **3.5** Add `"borrower_insurance_rate"` to `MortgageForm.Meta.fields` and `widgets`
- [x] **3.6** Add `country` kwarg to `MortgageForm.__init__()` — hide `insurance_premium`/`term_years` for FR, hide `borrower_insurance_rate` for CA
- [x] **3.7** Update `MortgageForm` amortization label for FR: "Loan duration (years)"
- [x] **3.8** Add `country` kwarg to `PropertyTaxForm.__init__()` — filter `tax_type` choices by country
- [x] **3.9** Define `CA_TAX_TYPES` and `FR_TAX_TYPES` class constants on `PropertyTaxForm`
- [x] **3.10** Split `FIELD_TOOLTIPS` into base + `FIELD_TOOLTIPS_CA` + `FIELD_TOOLTIPS_FR`
- [x] **3.11** Update `_apply_tooltips()` to accept `country` parameter and apply overrides

### Phase 4: Views — Pass Country Through ✅
- [x] **4.1** Update `property_create` — read `country` from POST data, pass to `MortgageForm(country=country)`
- [x] **4.2** Update `property_edit` — pass `country=prop.country` to `MortgageForm`
- [x] **4.3** Update `add_tax` — pass `country=prop.country` to `PropertyTaxForm`
- [x] **4.4** Update `edit_tax` — pass `country=prop.country` to `PropertyTaxForm`
- [x] **4.5** Update `property_detail` — use `get_tooltips(prop.country)` instead of `TERM_TOOLTIPS`
- [x] **4.6** Update `amortization_view` — pass `property` to template context (needed for country check in template)
- [x] **4.7** Update `sale_simulator` — pass `property` to template context for `sale_estimate.html`
- [x] **4.8** Verify all existing view tests still pass

### Phase 5: Templates — Country-Aware Display ✅
- [x] **5.1** Update `create.html` — add Alpine.js `propertyForm()` component wrapping the form
- [x] **5.2** Update `create.html` — render country field first in the Property details card
- [x] **5.3** Update `create.html` — conditional province/département label using `x-show` or `x-text`
- [x] **5.4** Update `create.html` — conditional welcome_tax label (Welcome tax vs Frais de notaire) using `x-text`
- [x] **5.5** Update `create.html` — conditional mortgage field visibility (insurance_premium/term_years for CA, borrower_insurance_rate for FR) using `x-show`
- [x] **5.6** Update `create.html` JS — add country-aware CMHC logic guard (skip for FR)
- [x] **5.7** Update `create.html` JS — add frais de notaire auto-estimate for FR (~8% of purchase price)
- [x] **5.8** Update `create.html` JS — auto-set currency to EUR when country switches to FR
- [x] **5.9** Update `create.html` JS — clear province default when country switches to FR
- [x] **5.10** Update `detail.html` — country-aware tax card title ("Property Taxes" for CA, "Taxes & Charges" for FR)
- [x] **5.11** Update `amortization.html` — add conditional Insurance column in `<thead>` and `<tbody>` for FR mortgages with borrower insurance
- [x] **5.12** Update `sale_estimate.html` — add French capital gains breakdown section (holding period, IR, PS, abatements, surtax) after capital_gains_tax row
- [x] **5.13** Update `edit.html` — same conditional field logic as create.html (country-aware labels, mortgage field visibility)

### Phase 6: Tooltips — Country-Aware Educational Content ✅
- [x] **6.1** Extract current Canada-specific tooltips from `TERM_TOOLTIPS` into `TERM_TOOLTIPS_CA` dict (amortization, agent_commission, capital_gains_tax, insurance_premium)
- [x] **6.2** Create `TERM_TOOLTIPS_FR` dict — French-specific tooltips (amortization, agent_commission, capital_gains_tax, borrower_insurance_rate, frais_notaire, taxe_fonciere, taxe_habitation, ifi)
- [x] **6.3** Keep base `TERM_TOOLTIPS` with country-agnostic entries (value, equity, mortgage, your_share, purchase_price, etc.)
- [x] **6.4** Implement `get_tooltips(country)` function — merge base + country overlay
- [x] **6.5** Update all views that pass `tips` to templates to use `get_tooltips(prop.country)`

### Phase 7: Form Field Tooltips ✅
- [x] **7.1** Create `FIELD_TOOLTIPS_CA` dict — Canada-specific field help texts (welcome_tax, insurance_premium, amortization, term_years, municipal_assessment)
- [x] **7.2** Create `FIELD_TOOLTIPS_FR` dict — France-specific field help texts (welcome_tax→frais de notaire, borrower_insurance, amortization, municipal_assessment→valeur cadastrale)
- [x] **7.3** Update `_apply_tooltips(form, country)` — apply base then country overlay
- [x] **7.4** Update `PropertyForm.__init__()` to pass country to `_apply_tooltips()`
- [x] **7.5** Update `MortgageForm.__init__()` to pass country to `_apply_tooltips()`

### Phase 8: JavaScript — Country-Aware Auto-Calculations ✅
- [x] **8.1** Guard `getCmhcRate()` / `updateInsurance()` to only run when country=CA
- [x] **8.2** Add `updateFraisNotaire()` — auto-estimate ~8% of purchase price when country=FR and field not manually edited
- [x] **8.3** Wire country select change to `updateAll()` — recalculate principal, insurance, frais when country changes
- [x] **8.4** Auto-set currency dropdown to EUR when country=FR (unless user manually changed it)
- [x] **8.5** Clear province field default when switching to FR

### Phase 9: Exchange Rates ✅
- [x] **9.1** Verify `exchange_rates.py` already handles EUR↔CAD — no changes expected
- [x] **9.2** Verify `CURRENCY_SYMBOLS` in `real_estate_filters.py` has EUR entry — already present

### Phase 10: Tests — French-Specific ✅
- [x] **10.1** Add `TestFrenchMonthlyRate` — fixed rate uses `r/12`, variable same as fixed, FR rate > CA rate at same nominal
- [x] **10.2** Add `TestFrenchMonthlyPayment` — standard 200k/3.5%/20yr French mortgage, borrower insurance adds to monthly cost
- [x] **10.3** Add `TestFrenchAmortizationSchedule` — verify schedule uses proportional rate, insurance entry in each row
- [x] **10.4** Add `TestFrenchCapitalGainsTax` — primary exempt, <5yr no abatement, 10yr partial abatement, 22yr IR exempt, 30yr fully exempt, no gain no tax
- [x] **10.5** Add `TestFrenchSurtax` — under 50k=0, 100k bracket, 260k+ bracket, boundary values
- [x] **10.6** Add `TestFrenchSaleSimulation` — TVA on commission (1.20), primary no CGT, rental has CGT with details dict
- [x] **10.7** Add `TestCreateFrenchProperty` — POST create with country=FR, verify country/currency saved
- [x] **10.8** Add `TestFrenchPropertyWithMortgage` — POST create with borrower_insurance_rate, verify saved correctly
- [x] **10.9** Add `TestFrenchTaxTypes` — POST add taxe_fonciere to FR property, verify created
- [x] **10.10** Add `TestFrenchPropertyDetail` — GET detail page for FR property, verify no errors
- [x] **10.11** Add `TestFrenchAmortizationView` — GET amortization page for FR mortgage, verify insurance column
- [x] **10.12** Add `TestFrenchSaleSimulatorView` — GET sale simulator for FR property, verify capital_gains_details in response
- [x] **10.13** Verify all existing Canadian tests still pass (full regression)

### Phase 11: Translations ✅
- [x] **11.1** Add country name translations (Canada, France)
- [x] **11.2** Add French tax type translations (Taxe foncière, Taxe d'habitation, IFI)
- [x] **11.3** Add French mortgage term translations (Mixed/taux mixte, borrower insurance rate, Loan duration)
- [x] **11.4** Add French form label translations (Département, Frais de notaire, Frais d'agence, Valeur cadastrale)
- [x] **11.5** Add French expense type translations (Charges de copropriété, Assurance emprunteur)
- [x] **11.6** Add French sale simulation translations (Holding period, Income tax 19%, Social contributions, Surtax, IR/Social abatement)
- [x] **11.7** Add French tooltip translations (Taxes & Charges)
- [x] **11.8** Run `uv run python manage.py compilemessages` to compile .mo file

### Phase 12: Final Verification ✅
- [x] **12.1** Run full test suite: `uv run pytest` — all 168 tests pass (existing + 28 new French tests)
- [x] **12.2** Run linter: `uv run ruff check . && uv run ruff format --check .` — all clean
- [x] **12.3** Run Vite build: `cd frontend && npm run build` — no errors
- [ ] **12.4** Manual smoke test: create a Canadian property — verify nothing changed
- [ ] **12.5** Manual smoke test: create a French property with mortgage — verify correct labels, insurance, currency
- [ ] **12.6** Manual smoke test: sale simulator on French rental — verify capital gains breakdown with abatements
- [ ] **12.7** Manual smoke test: amortization schedule on French mortgage — verify insurance column shows
- [ ] **12.8** Manual smoke test: add taxe foncière to French property — verify French tax types in dropdown
- [ ] **12.9** Manual smoke test: toggle currency on French property — verify EUR↔CAD conversion works
- [ ] **12.10** Commit all changes

---

### Task Count Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1. Models | 8 | Schema changes + migration |
| 2. Services | 13 | Mortgage math + capital gains + sale simulation |
| 3. Forms | 11 | Country-aware fields, labels, tooltips |
| 4. Views | 8 | Pass country to forms and tooltips |
| 5. Templates | 13 | Alpine.js country switcher, conditional display |
| 6. Tooltips | 5 | Country-specific educational content |
| 7. Form tooltips | 5 | Country-specific field help texts |
| 8. JavaScript | 5 | CMHC guard, frais auto-calc, currency sync |
| 9. Exchange rates | 2 | Verify existing support (no changes) |
| 10. Tests | 13 | French-specific + regression |
| 11. Translations | 8 | FR locale strings |
| 12. Verification | 10 | Tests, lint, build, smoke tests |
| **Total** | **101** | |
