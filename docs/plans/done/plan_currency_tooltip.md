# Plan: Currency Support, Auto-Share Calculation, Tooltips & Form Fix

## Issues to solve

1. **Co-owner section color**: The collapsible co-owner panel in `create.html` uses `bg-bg-subtle` which renders as a gray tint — but it's inside a white card, so it looks washed out. Switch to a warmer, more intentional tint.
2. **Auto-calculate share from down payments**: When creating a property, the co-owner share should auto-calculate from `down_payment` and `co_owner_down_payment` relative to `purchase_price` (e.g., if you put $50k down on a $400k property and co-owner puts $50k, shares are 50/50).
3. **Multi-currency support**: Add CAD/EUR currency choice per property, store it, display the right symbol, and offer a "converted equivalent" toggle based on live exchange rates.
4. **Educational tooltips**: Add `?` tooltips on every financial term in the detail page, list page, sale simulator, and amortization page — explaining each term in plain language.

---

## 1. Co-owner section styling fix

### Problem

The co-owner collapsible section uses `bg-bg-subtle` (stone-100, #f5f5f4) inside a white card, giving a flat gray look.

### Fix

Replace with a soft primary tint border treatment — no background fill, just a left accent and subtle border.

```html
<!-- templates/real_estate/create.html — line 49 -->
<!-- Before -->
<div x-show="hasCoOwner" x-transition class="rounded-xl border border-border bg-bg-subtle p-4 space-y-4">

<!-- After -->
<div x-show="hasCoOwner" x-transition class="rounded-xl border border-primary-200 border-l-[3px] border-l-primary-400 bg-primary-50/30 p-4 space-y-4">
```

This uses the same left-accent pattern as active nav items and unread notifications — consistent with the design system.

### Files changed
- `templates/real_estate/create.html` — line 49

---

## 2. Auto-calculate share from down payments

### Current behavior

- User enters `co_owner_share` manually as a percentage
- JS calculates `your_share = 100 - co_owner_share`
- `co_owner_down_payment` has no effect on share calculation

### New behavior

- When `purchase_price`, `down_payment`, and `co_owner_down_payment` are all filled, auto-calculate:
  - `co_owner_share = co_owner_down_payment / (down_payment + co_owner_down_payment) * 100`
  - `your_share = 100 - co_owner_share`
- The share field is still editable (user can override)
- Mark share as "dirty" if user manually types in it — stop auto-calculating
- Show a hint like "Based on down payments" next to the auto-calculated share

### Implementation

Update the existing `<script>` block in `create.html`:

```javascript
// Add to the existing DOMContentLoaded handler:

let shareDirty = false;
if (coOwnerShare) {
  coOwnerShare.addEventListener('input', function () { shareDirty = true; });
}

function updateShareFromDownPayments() {
  if (shareDirty || !coOwnerShare) return;
  const yourDown = parseFloat(downPayment?.value) || 0;
  const coDown = parseFloat(coOwnerDownPayment?.value) || 0;
  const totalDown = yourDown + coDown;
  if (totalDown > 0 && coDown > 0) {
    const coShare = (coDown / totalDown) * 100;
    coOwnerShare.value = coShare.toFixed(2);
    updateYourShare();
    // Show hint
    shareHint.textContent = '(based on down payments)';
    shareHint.classList.remove('hidden');
  }
}

// Wire up existing listeners to also call updateShareFromDownPayments
if (downPayment) downPayment.addEventListener('input', function() { updateAll(); updateShareFromDownPayments(); });
if (coOwnerDownPayment) coOwnerDownPayment.addEventListener('input', function() { updateAll(); updateShareFromDownPayments(); });
```

Add a hint `<span>` next to the share field:

```html
<!-- After co_owner_share field -->
<p class="mt-2 text-sm text-text-muted">
  {% trans "Your share" %}: <span id="your-share-display" class="font-semibold text-text">—</span>
  <span id="share-hint" class="hidden text-xs text-text-faint ml-2"></span>
</p>
```

### Files changed
- `templates/real_estate/create.html` — JS block + template hint

---

## 3. Multi-currency support (CAD / EUR)

This is the most significant change. It touches models, forms, views, template filters, and templates.

### 3.1 — Model: Add `currency` field to Property

```python
# apps/real_estate/models.py

class Property(models.Model):
    CURRENCY_CHOICES = [
        ("CAD", _("Canadian Dollar (CAD)")),
        ("EUR", _("Euro (EUR)")),
    ]

    # Add after postal_code:
    currency = models.CharField(
        _("currency"),
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="CAD",
    )
    # ... rest of fields unchanged
```

Migration: `python manage.py makemigrations real_estate`

### 3.2 — Exchange rate service

Create a new service module that fetches and caches exchange rates.

```python
# apps/real_estate/exchange_rates.py

import logging
from decimal import Decimal
from functools import lru_cache
from datetime import datetime

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Fallback rates (updated manually as a safety net)
FALLBACK_RATES = {
    ("CAD", "EUR"): Decimal("0.67"),
    ("EUR", "CAD"): Decimal("1.49"),
}

CACHE_KEY = "exchange_rates"
CACHE_TTL = 3600  # 1 hour


def get_exchange_rates():
    """Return a dict of {(from, to): Decimal rate} for supported currencies.

    Uses the free exchangerate.host API (no API key needed).
    Falls back to hardcoded rates if API is unavailable.
    """
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    rates = _fetch_rates()
    if rates:
        cache.set(CACHE_KEY, rates, CACHE_TTL)
    return rates or FALLBACK_RATES


def _fetch_rates():
    """Fetch live rates from exchangerate.host (free, no key)."""
    import urllib.request
    import json

    try:
        # Base CAD, get EUR
        url = "https://open.er-api.com/v6/latest/CAD"
        req = urllib.request.Request(url, headers={"User-Agent": "Limpid/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        if data.get("result") == "success":
            eur_rate = Decimal(str(data["rates"]["EUR"]))
            return {
                ("CAD", "EUR"): eur_rate,
                ("EUR", "CAD"): (Decimal("1") / eur_rate).quantize(Decimal("0.0001")),
                ("CAD", "CAD"): Decimal("1"),
                ("EUR", "EUR"): Decimal("1"),
            }
    except Exception:
        logger.warning("Failed to fetch exchange rates, using fallback")

    return None


def convert(amount, from_currency, to_currency):
    """Convert an amount from one currency to another."""
    if from_currency == to_currency:
        return amount
    rates = get_exchange_rates()
    rate = rates.get((from_currency, to_currency))
    if rate is None:
        return None
    return (amount * rate).quantize(Decimal("0.01"))
```

### 3.3 — Template filter: generalize `cad` → `money` and add `convert_to`

```python
# apps/real_estate/templatetags/real_estate_filters.py

from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()

CURRENCY_SYMBOLS = {
    "CAD": "$",
    "EUR": "€",
}


def _format_with_commas(n):
    """Format an integer with comma thousands separators."""
    negative = n < 0
    s = str(abs(n))
    groups = []
    while s:
        groups.append(s[-3:])
        s = s[:-3]
    result = ",".join(reversed(groups))
    return f"-{result}" if negative else result


@register.filter
def cad(value):
    """Format a Decimal as Canadian dollars: $1,234 or $1,234.56.

    Kept for backward compatibility. Equivalent to money(value, 'CAD').
    """
    return money(value, "CAD")


@register.filter
def money(value, currency="CAD"):
    """Format a Decimal with the appropriate currency symbol."""
    if value is None:
        return ""
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    if value == value.to_integral_value():
        return f"{symbol}{_format_with_commas(int(value))}"
    formatted = f"{value:.2f}"
    parts = formatted.split(".")
    return f"{symbol}{_format_with_commas(int(parts[0]))}.{parts[1]}"


@register.filter
def convert_to(value, args):
    """Convert a value from one currency to another.

    Usage: {{ amount|convert_to:"CAD,EUR" }}
    """
    if value is None:
        return ""
    try:
        from_currency, to_currency = args.split(",")
    except ValueError:
        return ""
    from apps.real_estate.exchange_rates import convert
    result = convert(Decimal(str(value)), from_currency.strip(), to_currency.strip())
    if result is None:
        return ""
    return money(result, to_currency.strip())
```

### 3.4 — Context processor: inject exchange rate + toggle currency

Add a context processor so every page can access the user's preferred display currency and the exchange rate.

```python
# config/context_processors.py — add to existing file

def currency_context(request):
    """Inject the user's display currency preference into every template."""
    display_currency = request.session.get("display_currency", None)  # None = native
    return {
        "display_currency": display_currency,
    }
```

Register in `config/settings/base.py` → `TEMPLATES[0].OPTIONS.context_processors`.

### 3.5 — Currency toggle view (HTMX)

A tiny view to switch the display currency in the session:

```python
# apps/real_estate/views.py — add

@login_required
def toggle_currency(request):
    """Toggle between native and converted display."""
    current = request.session.get("display_currency")
    # Cycle: None (native) → "CAD" → "EUR" → None
    if current is None:
        request.session["display_currency"] = "EUR"
    elif current == "EUR":
        request.session["display_currency"] = "CAD"
    else:
        request.session["display_currency"] = None
    # Redirect back
    return redirect(request.META.get("HTTP_REFERER", "/"))
```

URL:
```python
path("currency/toggle/", views.toggle_currency, name="toggle_currency"),
```

### 3.6 — Form: Add currency field

```python
# apps/real_estate/forms.py — PropertyForm.Meta.fields, add "currency"

fields = [
    "name",
    "property_type",
    "usage",
    "currency",    # NEW
    "address",
    # ...
]

# Widget:
"currency": forms.Select(attrs={"class": TAILWIND_SELECT_CLASS}),
```

### 3.7 — Template: Currency-aware display

Create a new component `templates/components/currency_value.html` for showing native + converted values:

```html
<!-- templates/components/currency_value.html -->
{% load real_estate_filters %}
<span class="font-mono tabular-nums">{{ value|money:currency }}</span>
{% if display_currency and display_currency != currency %}
<span class="text-xs text-text-faint ml-1">({{ value|convert_to:conversion_key }})</span>
{% endif %}
```

However, this approach is complex to thread through every `metric_row` and `stat_card` include. A simpler approach:

**Pass `property.currency` into the template context and update the `cad` filter calls to use `money`.**

In `detail.html`, replace `|cad` with `|money:property.currency`:

```django
{% include "components/stat_card.html" with label=_("Value") value=snapshot.current_valuation|money:property.currency %}
```

And for the converted equivalent, add a toggle button at the top of the detail page:

```html
<!-- Currency toggle button at top of detail page -->
<button hx-post="{% url 'real_estate:toggle_currency' %}"
        hx-target="body"
        hx-swap="none"
        class="btn-ghost text-xs">
  {% if display_currency %}
    {% trans "Show in" %} {{ property.currency }}
  {% else %}
    {% trans "Convert to" %} {% if property.currency == "CAD" %}EUR{% else %}CAD{% endif %}
  {% endif %}
</button>
```

### 3.8 — Update TAILWIND_INPUT_CLASS (bonus fix)

Both `TAILWIND_INPUT_CLASS` and `TAILWIND_SELECT_CLASS` still use the old design system classes (`shadow-sm`, `rounded-lg`, `focus:ring-1`). Replace with the new `.input` class:

```python
# apps/real_estate/forms.py
TAILWIND_INPUT_CLASS = "input"

# apps/accounts/forms.py
TAILWIND_SELECT_CLASS = "input"
```

### Files changed
| File | Change |
|------|--------|
| `apps/real_estate/models.py` | Add `currency` field to `Property` |
| `apps/real_estate/exchange_rates.py` | **New** — exchange rate fetching + caching |
| `apps/real_estate/templatetags/real_estate_filters.py` | Add `money` and `convert_to` filters |
| `apps/real_estate/forms.py` | Add `currency` to `PropertyForm`, update `TAILWIND_INPUT_CLASS` |
| `apps/accounts/forms.py` | Update `TAILWIND_SELECT_CLASS` to `"input"` |
| `apps/real_estate/views.py` | Add `toggle_currency` view |
| `apps/real_estate/urls.py` | Add `currency/toggle/` URL |
| `config/context_processors.py` | Add `currency_context` |
| `config/settings/base.py` | Register `currency_context` processor |
| `templates/real_estate/detail.html` | Replace `\|cad` → `\|money:property.currency`, add toggle button |
| `templates/real_estate/list.html` | Replace `\|cad` → `\|money:item.property.currency` |
| `templates/real_estate/partials/*.html` | Replace `\|cad` → `\|money:property.currency` |
| `templates/real_estate/amortization.html` | Replace `\|cad` → `\|money:property.currency` |
| Migration | Add `currency` field (default "CAD") |

---

## 4. Educational tooltips on all financial terms

### Approach

Create a dictionary of financial term tooltips (similar to `FIELD_TOOLTIPS` in `forms.py`, but for display terms rather than form fields). Use `{% include "components/tooltip.html" %}` next to each label.

### 4.1 — Define tooltips dictionary

```python
# apps/real_estate/tooltips.py (new file)

from django.utils.translation import gettext_lazy as _

# Tooltips for financial terms displayed on detail/list pages
TERM_TOOLTIPS = {
    "value": _(
        "The estimated current market value of the entire property. "
        "This is what you'd expect to sell it for today."
    ),
    "equity": _(
        "The portion of the property you truly own — the value minus what you still owe on the mortgage. "
        "Think of it as your 'net worth' in this property."
    ),
    "mortgage": _(
        "The remaining amount you owe to the bank. "
        "This decreases with each payment as you pay down the principal."
    ),
    "your_share": _(
        "Your personal portion of the equity, based on your ownership percentage. "
        "If you own 50% of a property with $200k equity, your share is $100k."
    ),
    "purchase_price": _(
        "The total price you paid for the property when you bought it, before taxes and closing costs."
    ),
    "appreciation": _(
        "How much the property value has increased (or decreased) since you bought it. "
        "Calculated as: current value minus purchase price."
    ),
    "your_valuation_share": _(
        "Your portion of the total property value, based on your ownership percentage."
    ),
    "your_mortgage_share": _(
        "Your portion of the remaining mortgage debt, based on your ownership percentage."
    ),
    "down_payment": _(
        "The cash you contributed upfront when purchasing the property. "
        "A larger down payment means less mortgage debt and lower insurance costs."
    ),
    "principal_paid": _(
        "The total amount of mortgage principal you've paid off so far. "
        "This is the portion of your payments that actually reduces your debt."
    ),
    "monthly_payment": _(
        "Your regular mortgage payment amount, including both principal and interest. "
        "Principal reduces your debt; interest is the cost of borrowing."
    ),
    "remaining_balance": _(
        "How much you still owe on the mortgage. "
        "This decreases with each payment as you chip away at the principal."
    ),
    "amortization": _(
        "The total number of years to fully pay off the mortgage. "
        "In Canada, 25 years is the most common amortization period."
    ),
    "rate": _(
        "The annual interest rate on your mortgage. "
        "Fixed means it stays the same for your term; variable means it can change with the market."
    ),
    "sale_price": _(
        "The assumed selling price. By default, this is your current property valuation. "
        "Adjust it to simulate different scenarios."
    ),
    "gross_equity": _(
        "Sale price minus the remaining mortgage. This is what you'd have before paying selling costs."
    ),
    "agent_commission": _(
        "The real estate agent's fee, typically 4-6% of the sale price in Canada. "
        "This includes applicable sales taxes (GST/QST)."
    ),
    "notary_fees": _(
        "Legal fees for the sale transaction, paid to the notary who handles the paperwork."
    ),
    "capital_gains_tax": _(
        "If this isn't your primary residence, you may owe tax on the profit. "
        "In Canada, 50% of the capital gain is taxable at your marginal rate."
    ),
    "total_costs": _(
        "All costs associated with selling: agent fees, notary fees, and taxes."
    ),
    "net_proceeds": _(
        "What you actually take home after selling — the sale price minus the mortgage and all selling costs. "
        "This is your real profit from the sale."
    ),
    "equity_breakdown": _(
        "A visual split of how much of the property value is yours (equity) vs. still owed to the bank."
    ),
    "payment_breakdown": _(
        "How your mortgage payments are split between principal (paying down debt) and interest (cost of borrowing)."
    ),
    "expenses_by_type": _(
        "A breakdown of all expenses you've recorded by category — renovations, maintenance, insurance, etc."
    ),
    "ownership": _(
        "Who owns this property and their respective share percentages. "
        "Shares can change when co-owners are added or removed."
    ),
    "lender": _(
        "The bank or financial institution that provided your mortgage."
    ),
    "your_equity": _(
        "Your personal equity — how much of the property's net value belongs to you. "
        "Calculated as: total equity multiplied by your ownership percentage."
    ),
}
```

### 4.2 — Pass tooltips to templates via views

In `property_detail` view, add tooltips to context:

```python
# apps/real_estate/views.py — property_detail

from .tooltips import TERM_TOOLTIPS

def property_detail(request, pk):
    # ... existing code ...
    context = {
        # ... existing context ...
        "tips": TERM_TOOLTIPS,
    }
    return render(request, "real_estate/detail.html", context)
```

Similarly for `property_list`, `amortization_view`, `sale_simulator`.

### 4.3 — Update templates to include tooltips

#### Detail page — stat cards

```django
{# Stat cards row #}
<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
  {% include "components/stat_card.html" with label=_("Value") value=snapshot.current_valuation|cad tooltip_id="value" tooltip_text=tips.value %}
  {% with pct=snapshot.equity_pct|floatformat:1|add:"%" %}
  {% include "components/stat_card.html" with label=_("Equity") value=snapshot.equity|cad annotation=pct tooltip_id="equity" tooltip_text=tips.equity %}
  {% endwith %}
  {% include "components/stat_card.html" with label=_("Mortgage") value=snapshot.mortgage_balance|cad tooltip_id="mortgage" tooltip_text=tips.mortgage %}
  {% with pct=owner_snapshot.share_pct|floatformat:0|add:"%" %}
  {% include "components/stat_card.html" with label=_("Your share") value=owner_snapshot.your_equity|cad annotation=pct tooltip_id="your_share" tooltip_text=tips.your_share %}
  {% endwith %}
</div>
```

#### Update `stat_card.html` to support optional tooltip

```html
<!-- templates/components/stat_card.html -->
{% load i18n %}
<div class="rounded-2xl border border-border bg-bg-card p-4">
  <p class="text-[0.8125rem] font-medium uppercase tracking-wide text-text-muted">
    {{ label }}
    {% if tooltip_id %}
      {% include "components/tooltip.html" with id=tooltip_id text=tooltip_text %}
    {% endif %}
  </p>
  <p class="mt-1 text-[1.75rem] font-semibold tracking-tight text-text font-mono tabular-nums">{{ value }}</p>
  {% if annotation %}<p class="mt-0.5 text-sm text-text-faint">({{ annotation }})</p>{% endif %}
</div>
```

#### Update `metric_row.html` to support optional tooltip

```html
<!-- templates/components/metric_row.html -->
<div class="flex items-baseline justify-between py-2.5 border-b border-border/60 last:border-0">
  <dt class="text-sm text-text-muted">
    {{ label }}
    {% if tooltip_id %}
      {% include "components/tooltip.html" with id=tooltip_id text=tooltip_text %}
    {% endif %}
  </dt>
  <dd class="text-sm font-medium text-text font-mono tabular-nums">
    {{ value }}
    {% if annotation %}<span class="ml-1.5 text-xs text-text-faint">({{ annotation }})</span>{% endif %}
  </dd>
</div>
```

#### Detail page — metric rows with tooltips

```django
{# Property details card #}
{% include "components/metric_row.html" with label=_("Purchase price") value=snapshot.purchase_price|cad tooltip_id="purchase_price" tooltip_text=tips.purchase_price %}
{% include "components/metric_row.html" with label=_("Appreciation") value=snapshot.appreciation|cad annotation=pct tooltip_id="appreciation" tooltip_text=tips.appreciation %}
{% include "components/metric_row.html" with label=_("Your valuation share") value=owner_snapshot.your_valuation|cad tooltip_id="your_valuation_share" tooltip_text=tips.your_valuation_share %}
{% include "components/metric_row.html" with label=_("Your mortgage share") value=owner_snapshot.your_mortgage_share|cad tooltip_id="your_mortgage_share" tooltip_text=tips.your_mortgage_share %}
{% include "components/metric_row.html" with label=_("Down payment") value=owner_snapshot.your_contributions.down_payment|cad tooltip_id="down_payment" tooltip_text=tips.down_payment %}
{% include "components/metric_row.html" with label=_("Principal paid") value=owner_snapshot.your_contributions.principal_paid|cad tooltip_id="principal_paid" tooltip_text=tips.principal_paid %}
```

#### Detail page — chart titles

```django
{% include "components/card_start.html" with title=_("Equity Breakdown") tooltip_id="equity_breakdown" tooltip_text=tips.equity_breakdown %}
{% include "components/card_start.html" with title=_("Payment Breakdown") tooltip_id="payment_breakdown" tooltip_text=tips.payment_breakdown %}
{% include "components/card_start.html" with title=_("Expenses by Type") tooltip_id="expenses_by_type" tooltip_text=tips.expenses_by_type %}
```

#### Update `card_start.html` to support optional tooltip

Add tooltip support to the card title:

```html
<!-- In card_start.html, after the title text -->
{% if title %}
<h3 class="...">
  {{ title }}
  {% if tooltip_id %}
    {% include "components/tooltip.html" with id=tooltip_id text=tooltip_text %}
  {% endif %}
</h3>
{% endif %}
```

#### Detail page — mortgage card

```django
{% include "components/metric_row.html" with label=_("Lender") value=mortgage.lender tooltip_id="lender" tooltip_text=tips.lender %}
{% include "components/metric_row.html" with label=_("Rate") value=rate annotation=rtype tooltip_id="rate" tooltip_text=tips.rate %}
{% include "components/metric_row.html" with label=_("Monthly payment") value=snapshot.monthly_payment|cad tooltip_id="monthly_payment" tooltip_text=tips.monthly_payment %}
{% include "components/metric_row.html" with label=_("Remaining balance") value=snapshot.mortgage_balance|cad tooltip_id="remaining_balance" tooltip_text=tips.remaining_balance %}
{% include "components/metric_row.html" with label=_("Amortization") value=mortgage.amortization_years annotation=_("years") tooltip_id="amortization" tooltip_text=tips.amortization %}
```

#### Sale simulator partial

```django
{% include "components/metric_row.html" with label=_("Sale price") value=estimate.sale_price|cad tooltip_id="sale_price" tooltip_text=tips.sale_price %}
{% include "components/metric_row.html" with label=_("Gross equity") value=estimate.gross_equity|cad tooltip_id="gross_equity" tooltip_text=tips.gross_equity %}
{% include "components/metric_row.html" with label=_("Agent commission (incl. tax)") value=estimate.agent_commission|cad tooltip_id="agent_commission" tooltip_text=tips.agent_commission %}
{% include "components/metric_row.html" with label=_("Notary fees") value=estimate.notary_fees|cad tooltip_id="notary_fees" tooltip_text=tips.notary_fees %}
{% include "components/metric_row.html" with label=_("Capital gains tax (est.)") value=estimate.capital_gains_tax|cad tooltip_id="capital_gains_tax" tooltip_text=tips.capital_gains_tax %}
{% include "components/metric_row.html" with label=_("Total costs") value=estimate.total_costs|cad tooltip_id="total_costs" tooltip_text=tips.total_costs %}
```

Note: `sale_estimate.html` is rendered via HTMX, so `tips` needs to be passed through the `sale_simulator` view context.

#### List page

```django
<!-- In the property card -->
<div class="flex items-baseline justify-between">
  <span class="text-sm text-text-muted">
    {% trans "Value" %}
    {% include "components/tooltip.html" with id="list_value_"|add:item.property.pk text=tips.value %}
  </span>
  <span class="text-lg font-semibold text-text font-mono">{{ item.snapshot.current_valuation|cad }}</span>
</div>
<div class="flex items-baseline justify-between">
  <span class="text-sm text-text-muted">
    {% trans "Your equity" %}
    {% include "components/tooltip.html" with id="list_equity_"|add:item.property.pk text=tips.your_equity %}
  </span>
  <span class="font-semibold text-primary-600 font-mono">{{ item.snapshot.your_equity|cad }}</span>
</div>
```

### 4.4 — French translations for all tooltips

Add to `locale/fr/LC_MESSAGES/django.po`:

```po
# ── Educational tooltips (detail page) ──
msgid "The estimated current market value of the entire property. This is what you'd expect to sell it for today."
msgstr "La valeur marchande estimée de la propriété complète. C'est le prix auquel vous vous attendriez à la vendre aujourd'hui."

msgid "The portion of the property you truly own — the value minus what you still owe on the mortgage. Think of it as your 'net worth' in this property."
msgstr "La partie de la propriété qui vous appartient vraiment — la valeur moins ce que vous devez encore sur l'hypothèque. C'est votre « valeur nette » dans cette propriété."

msgid "The remaining amount you owe to the bank. This decreases with each payment as you pay down the principal."
msgstr "Le montant qu'il vous reste à rembourser à la banque. Il diminue à chaque paiement au fur et à mesure que vous remboursez le capital."

msgid "Your personal portion of the equity, based on your ownership percentage. If you own 50% of a property with $200k equity, your share is $100k."
msgstr "Votre part personnelle de l'équité, basée sur votre pourcentage de propriété. Si vous possédez 50% d'une propriété avec 200k$ d'équité, votre part est de 100k$."

# ... (all other tooltips follow same pattern)
```

### Files changed
| File | Change |
|------|--------|
| `apps/real_estate/tooltips.py` | **New** — all educational tooltip texts |
| `apps/real_estate/views.py` | Add `tips` to `property_detail`, `property_list`, `sale_simulator`, `amortization_view` contexts |
| `templates/components/stat_card.html` | Add optional `tooltip_id`/`tooltip_text` support |
| `templates/components/metric_row.html` | Add optional `tooltip_id`/`tooltip_text` support |
| `templates/components/card_start.html` | Add optional `tooltip_id`/`tooltip_text` support |
| `templates/real_estate/detail.html` | Add tooltips to all stat cards, metric rows, and card titles |
| `templates/real_estate/list.html` | Add tooltips to Value and Your equity labels |
| `templates/real_estate/partials/sale_estimate.html` | Add tooltips to all metric rows |
| `templates/real_estate/amortization.html` | Add tooltips to summary metrics |
| `locale/fr/LC_MESSAGES/django.po` | French translations for all tooltip texts |

---

## Detailed TODO list

### Phase 1 — Quick fixes (co-owner styling + share auto-calc)

- [x] **1.1 — Fix co-owner section color in `create.html`**
  - Change `bg-bg-subtle` to `bg-primary-50/30` + `border-primary-200` + `border-l-[3px] border-l-primary-400`
  - File: `templates/real_estate/create.html` line 49

- [x] **1.2 — Auto-calculate share from down payments**
  - Add `shareDirty` flag to JS, triggered on manual `coOwnerShare` input
  - Add `updateShareFromDownPayments()` function
  - Wire `downPayment` and `coOwnerDownPayment` `input` events to call it
  - Add `<span id="share-hint">` next to your-share display
  - File: `templates/real_estate/create.html` — JS block + template

- [x] **1.3 — Update `TAILWIND_INPUT_CLASS` and `TAILWIND_SELECT_CLASS`**
  - Change `TAILWIND_INPUT_CLASS` in `apps/real_estate/forms.py` from old inline classes to `"input"`
  - Change `TAILWIND_SELECT_CLASS` in `apps/accounts/forms.py` from old inline classes to `"input"`
  - Files: `apps/real_estate/forms.py`, `apps/accounts/forms.py`

- [x] **1.4 — Verify forms render correctly**
  - Check create property form, edit form, expense/tax/valuation forms
  - Verify `.input` class applies to all form widgets

---

### Phase 2 — Educational tooltips

- [x] **2.1 — Create `apps/real_estate/tooltips.py`**
  - Define `TERM_TOOLTIPS` dictionary with ~25 educational tooltip texts
  - All strings wrapped in `gettext_lazy`
  - File: `apps/real_estate/tooltips.py` (new)

- [x] **2.2 — Update `stat_card.html` for tooltip support**
  - Add conditional `{% if tooltip_id %}{% include tooltip %}{% endif %}` next to label
  - File: `templates/components/stat_card.html`

- [x] **2.3 — Update `metric_row.html` for tooltip support**
  - Add conditional tooltip include next to `<dt>` label
  - File: `templates/components/metric_row.html`

- [x] **2.4 — Update `card_start.html` for tooltip support**
  - Add conditional tooltip include after title `<h3>` text
  - File: `templates/components/card_start.html`

- [x] **2.5 — Pass `tips` context from views**
  - Import `TERM_TOOLTIPS` as `tips` in `property_detail`, `property_list`, `sale_simulator`, `amortization_view`
  - Add `"tips": TERM_TOOLTIPS` to each view's context dict
  - File: `apps/real_estate/views.py`

- [x] **2.6 — Add tooltips to `detail.html`**
  - Stat cards: Value, Equity, Mortgage, Your share
  - Details card: Purchase price, Appreciation, Your valuation share, Your mortgage share, Down payment, Principal paid
  - Charts: Equity Breakdown, Payment Breakdown, Expenses by Type
  - Mortgage card: Lender, Rate, Monthly payment, Remaining balance, Amortization
  - Ownership card title
  - File: `templates/real_estate/detail.html`

- [x] **2.7 — Add tooltips to `sale_estimate.html`**
  - Sale price, Mortgage balance, Gross equity, Agent commission, Notary fees, Capital gains tax, Total costs, Net proceeds
  - File: `templates/real_estate/partials/sale_estimate.html`

- [x] **2.8 — Add tooltips to `list.html`**
  - Value and Your equity labels (use unique tooltip IDs per property card: `"list_value_" + pk`)
  - File: `templates/real_estate/list.html`

- [x] **2.9 — Add tooltips to `amortization.html`**
  - Monthly payment, Total interest paid, Total paid to date, Original principal, Annual rate, Amortization years
  - File: `templates/real_estate/amortization.html`

- [x] **2.10 — Add French translations for all tooltips**
  - Add ~25 msgid/msgstr pairs to `locale/fr/LC_MESSAGES/django.po`
  - Run `compilemessages`
  - File: `locale/fr/LC_MESSAGES/django.po`

- [x] **2.11 — Verify tooltips render**
  - Check desktop popover behavior (click open, click-outside close)
  - Check mobile bottom sheet behavior
  - Verify no tooltip ID collisions
  - Run tests

---

### Phase 3 — Multi-currency support

- [x] **3.1 — Add `currency` field to `Property` model**
  - Add `CURRENCY_CHOICES` (CAD, EUR)
  - Add `currency` CharField with default="CAD"
  - Generate and run migration
  - File: `apps/real_estate/models.py`

- [x] **3.2 — Create exchange rate service**
  - Create `apps/real_estate/exchange_rates.py`
  - Implement `get_exchange_rates()` with Django cache (1 hour TTL)
  - Use `open.er-api.com` free API (no key needed)
  - Implement `convert(amount, from_currency, to_currency)`
  - Add fallback rates for when API is down
  - File: `apps/real_estate/exchange_rates.py` (new)

- [x] **3.3 — Add `money` and `convert_to` template filters**
  - Add `CURRENCY_SYMBOLS` dict
  - Add `money(value, currency)` filter
  - Add `convert_to(value, "FROM,TO")` filter
  - Keep `cad` filter as alias for backward compatibility
  - File: `apps/real_estate/templatetags/real_estate_filters.py`

- [x] **3.4 — Add `currency` to PropertyForm**
  - Add `"currency"` to `Meta.fields` list
  - Add Select widget with `TAILWIND_SELECT_CLASS`
  - File: `apps/real_estate/forms.py`

- [x] **3.5 — Add currency context processor**
  - Create `currency_context` function in `config/context_processors.py`
  - Inject `display_currency` from session
  - Register in `config/settings/base.py`
  - Files: `config/context_processors.py`, `config/settings/base.py`

- [x] **3.6 — Add `toggle_currency` view and URL**
  - Create view that cycles display_currency in session (None → EUR → CAD → None)
  - Add URL pattern
  - Files: `apps/real_estate/views.py`, `apps/real_estate/urls.py`

- [x] **3.7 — Update `detail.html` for multi-currency**
  - Replace all `|cad` with `|money:property.currency`
  - Add currency toggle button in header area
  - When `display_currency` is set and differs from property currency, show converted values in parentheses
  - File: `templates/real_estate/detail.html`

- [x] **3.8 — Update `list.html` for multi-currency**
  - Replace `|cad` with `|money:item.property.currency`
  - File: `templates/real_estate/list.html`

- [x] **3.9 — Update partials for multi-currency**
  - `sale_estimate.html`: replace `|cad` → `|money:property.currency`
  - `expense_list.html`: same
  - `tax_list.html`: same
  - `valuation_history.html`: same
  - Files: `templates/real_estate/partials/*.html`

- [x] **3.10 — Update `amortization.html` for multi-currency**
  - Replace `|cad` → `|money:property.currency`
  - File: `templates/real_estate/amortization.html`

- [x] **3.11 — Add French translations for currency strings**
  - "Canadian Dollar (CAD)", "Euro (EUR)", "Show in", "Convert to"
  - Run `compilemessages`
  - File: `locale/fr/LC_MESSAGES/django.po`

- [x] **3.12 — Add tests for currency features**
  - Test `money` filter with CAD and EUR
  - Test `convert_to` filter
  - Test `exchange_rates.convert()` with mocked API response
  - Test `toggle_currency` view
  - Test property creation with EUR currency
  - File: `apps/real_estate/tests/test_services.py` or new test file

- [x] **3.13 — Verify everything**
  - Run full test suite
  - Run Vite build
  - Verify exchange rate fetching works
  - Verify fallback rates work (disconnect network)
  - Check all pages with CAD property and EUR property
