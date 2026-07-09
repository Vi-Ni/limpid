# Real Estate & Patrimony Management — Implementation Plan

## Context

Limpid currently tracks financial portfolios (stocks, ETFs, bonds). The goal is to evolve it into a **full patrimony management tool** covering all asset types, starting with **real estate** — the most complex and highest-value asset class for most Canadians.

Real estate is hard to track because of: shared ownership with evolving splits, amortization schedules, accumulated renovations, tax implications on sale, and the difficulty of knowing "what would I actually get if I sold today?"

---

## What Is "Patrimoine"? (Exhaustive List)

The dashboard will eventually cover all these categories:

### Assets
| Category | Examples |
|----------|----------|
| **Cash & Deposits** | Chequing, savings, HISA |
| **Registered Accounts** | RRSP, TFSA, RESP, RDSP, FHSA |
| **Stocks** | Individual equities (TSX, NYSE) |
| **ETFs** | Index, sector, bond ETFs |
| **Mutual Funds** | Actively managed, balanced |
| **Bonds** | Government, provincial, corporate |
| **GICs** | Fixed-term, cashable |
| **Crypto** | Bitcoin, Ethereum, etc. |
| **Real Estate** | Primary residence, rental, condo, land, cottage |
| **Vehicles** | Cars, boats, RVs |
| **Art & Collectibles** | Paintings, wine, rare coins, watches |
| **Business Interests** | CCPC shares, partnerships, sole proprietorships |
| **Pensions** | Employer DB/DC plans, QPP/CPP, OAS |
| **Insurance** | Whole life / universal life (cash surrender value) |

### Liabilities
| Category | Examples |
|----------|----------|
| **Mortgages** | Primary, rental, HELOC |
| **Loans** | Student, car, personal, business |
| **Credit Cards** | Outstanding balances |
| **Tax Liabilities** | Taxes owing to CRA/Revenu Québec |

**Phase 1 (this plan)**: Real estate only. Other asset types come later.

---

## Architecture Decision: New App `apps/real_estate/`

A new Django app rather than extending `apps/portfolio/`, because:
- Real estate has fundamentally different data (address, mortgage, co-owners, renovations) vs. financial assets (ticker, quantity, price)
- The existing portfolio app is tightly coupled to `Asset` (ticker-based) and `Holding` (quantity × price)
- Shared ownership between users is a new concept that doesn't exist in portfolio
- Clean separation now makes it easy to add a unified "patrimony dashboard" later that aggregates both

---

## Data Model

### Entity Relationship Diagram

```
User
 ├── PropertyOwnership (M2M through table)
 │    └── Property
 │         ├── Mortgage
 │         │    └── MortgagePayment (amortization schedule)
 │         ├── PropertyExpense (renovations, taxes, fees)
 │         ├── PropertyValuation (valuation history)
 │         └── OwnershipPeriod (split ratios over time)
 │              └── OwnershipPeriodShare (per-owner share in that period)
 └── (existing) Portfolio → Holding → Asset
```

### Models

```python
# apps/real_estate/models.py

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Property(models.Model):
    """A real estate property (house, condo, land, etc.)."""

    PROPERTY_TYPE_CHOICES = [
        ("house", _("House")),
        ("condo", _("Condo (divided co-ownership)")),
        ("condo_undivided", _("Condo (undivided co-ownership)")),
        ("duplex", _("Duplex")),
        ("triplex", _("Triplex")),
        ("land", _("Vacant land")),
        ("cottage", _("Cottage / Secondary residence")),
        ("commercial", _("Commercial property")),
    ]

    USAGE_CHOICES = [
        ("primary", _("Primary residence")),
        ("secondary", _("Secondary residence")),
        ("rental", _("Rental property")),
        ("commercial", _("Commercial")),
    ]

    name = models.CharField(_("name"), max_length=200)
    property_type = models.CharField(
        _("property type"), max_length=20, choices=PROPERTY_TYPE_CHOICES
    )
    usage = models.CharField(_("usage"), max_length=20, choices=USAGE_CHOICES)
    address = models.CharField(_("address"), max_length=500)
    city = models.CharField(_("city"), max_length=100)
    province = models.CharField(_("province"), max_length=50, default="QC")
    postal_code = models.CharField(_("postal code"), max_length=10, blank=True)

    # Acquisition
    purchase_price = models.DecimalField(
        _("purchase price"), max_digits=12, decimal_places=2
    )
    purchase_date = models.DateField(_("purchase date"))
    welcome_tax_paid = models.DecimalField(
        _("welcome tax paid"), max_digits=10, decimal_places=2, default=0
    )
    notary_fees_purchase = models.DecimalField(
        _("notary fees at purchase"), max_digits=10, decimal_places=2, default=0
    )

    # Current valuation
    current_valuation = models.DecimalField(
        _("current valuation"), max_digits=12, decimal_places=2
    )
    valuation_date = models.DateField(_("valuation date"))

    # Municipal assessment (for property tax calculation)
    municipal_assessment = models.DecimalField(
        _("municipal assessment"), max_digits=12, decimal_places=2, default=0
    )

    # Owners (M2M through PropertyOwnership)
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="PropertyOwnership",
        related_name="properties",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("property")
        verbose_name_plural = _("properties")
        ordering = ["-purchase_date"]

    def __str__(self):
        return self.name

    @property
    def total_invested(self):
        """Purchase price + welcome tax + notary + all expenses."""
        expenses_total = (
            self.expenses.aggregate(total=models.Sum("amount"))["total"] or 0
        )
        return (
            self.purchase_price
            + self.welcome_tax_paid
            + self.notary_fees_purchase
            + expenses_total
        )

    @property
    def total_appreciation(self):
        return self.current_valuation - self.purchase_price

    @property
    def total_appreciation_pct(self):
        if self.purchase_price:
            return (self.total_appreciation / self.purchase_price) * 100
        return Decimal("0")


class PropertyOwnership(models.Model):
    """Links a user to a property they co-own."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_ownerships",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="ownerships"
    )
    is_admin = models.BooleanField(
        _("can edit property"), default=False,
        help_text=_("Can this owner edit property details?"),
    )
    down_payment = models.DecimalField(
        _("down payment contributed"), max_digits=12, decimal_places=2, default=0
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "property")]
        verbose_name = _("property ownership")

    def __str__(self):
        return f"{self.user} — {self.property}"


class OwnershipPeriod(models.Model):
    """A period during which a specific ownership split applies.

    Example: 50/50 from 2020-01-01 to 2023-06-30,
             then 75/25 from 2023-07-01 onward.
    """

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="ownership_periods"
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"), null=True, blank=True)
    note = models.CharField(_("note"), max_length=200, blank=True)

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        end = self.end_date or "ongoing"
        return f"{self.property.name}: {self.start_date} → {end}"


class OwnershipPeriodShare(models.Model):
    """Each owner's share within an OwnershipPeriod."""

    period = models.ForeignKey(
        OwnershipPeriod, on_delete=models.CASCADE, related_name="shares"
    )
    owner = models.ForeignKey(
        PropertyOwnership, on_delete=models.CASCADE, related_name="period_shares"
    )
    share_pct = models.DecimalField(
        _("ownership share (%)"), max_digits=5, decimal_places=2
    )

    class Meta:
        unique_together = [("period", "owner")]

    def __str__(self):
        return f"{self.owner.user}: {self.share_pct}%"


class Mortgage(models.Model):
    """A mortgage on a property. A property can have multiple mortgages (refinance)."""

    RATE_TYPE_CHOICES = [
        ("fixed", _("Fixed")),
        ("variable", _("Variable")),
    ]

    PAYMENT_FREQUENCY_CHOICES = [
        ("monthly", _("Monthly")),
        ("biweekly", _("Bi-weekly")),
        ("accelerated_biweekly", _("Accelerated bi-weekly")),
    ]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="mortgages"
    )
    lender = models.CharField(_("lender"), max_length=200)
    principal = models.DecimalField(
        _("original principal"), max_digits=12, decimal_places=2
    )
    annual_rate = models.DecimalField(
        _("annual interest rate (%)"), max_digits=5, decimal_places=3
    )
    rate_type = models.CharField(
        _("rate type"), max_length=20, choices=RATE_TYPE_CHOICES, default="fixed"
    )
    amortization_years = models.PositiveSmallIntegerField(
        _("amortization (years)"), default=25
    )
    term_years = models.PositiveSmallIntegerField(_("term (years)"), default=5)
    payment_frequency = models.CharField(
        _("payment frequency"),
        max_length=30,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default="monthly",
    )
    start_date = models.DateField(_("start date"))
    is_active = models.BooleanField(_("active"), default=True)

    # Insurance (CMHC) — added to principal if down payment < 20%
    insurance_premium = models.DecimalField(
        _("mortgage insurance premium"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.lender} — {self.property.name}"

    @property
    def effective_principal(self):
        """Principal + insurance premium (total amount financed)."""
        return self.principal + self.insurance_premium

    @property
    def monthly_rate(self):
        """Convert Canadian semi-annual compounding to monthly rate."""
        r = self.annual_rate / 100
        if self.rate_type == "fixed":
            # Fixed: compounded semi-annually by law
            return (1 + r / 2) ** (Decimal("1") / 6) - 1
        else:
            # Variable: compounded monthly
            return r / 12

    @property
    def monthly_payment(self):
        """Standard amortization payment."""
        r = self.monthly_rate
        n = self.amortization_years * 12
        p = self.effective_principal
        if r == 0:
            return p / n
        return (r * p) / (1 - (1 + r) ** (-n))


class MortgagePayment(models.Model):
    """Individual payment in the amortization schedule.

    Can be auto-generated or manually recorded for tracking actual payments.
    """

    mortgage = models.ForeignKey(
        Mortgage, on_delete=models.CASCADE, related_name="payments"
    )
    payment_number = models.PositiveIntegerField(_("payment number"))
    date = models.DateField(_("payment date"))
    total_payment = models.DecimalField(
        _("total payment"), max_digits=10, decimal_places=2
    )
    principal_portion = models.DecimalField(
        _("principal portion"), max_digits=10, decimal_places=2
    )
    interest_portion = models.DecimalField(
        _("interest portion"), max_digits=10, decimal_places=2
    )
    balance_after = models.DecimalField(
        _("balance after payment"), max_digits=12, decimal_places=2
    )
    # Which owner paid this? (for split tracking)
    paid_by = models.ForeignKey(
        PropertyOwnership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mortgage_payments",
    )

    class Meta:
        ordering = ["payment_number"]
        unique_together = [("mortgage", "payment_number")]


class PropertyExpense(models.Model):
    """Renovations, repairs, property tax, insurance, condo fees, etc."""

    EXPENSE_TYPE_CHOICES = [
        ("renovation", _("Renovation / Improvement")),
        ("repair", _("Repair / Maintenance")),
        ("property_tax", _("Property tax")),
        ("insurance", _("Insurance")),
        ("condo_fees", _("Condo fees")),
        ("other", _("Other")),
    ]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="expenses"
    )
    expense_type = models.CharField(
        _("type"), max_length=20, choices=EXPENSE_TYPE_CHOICES
    )
    description = models.CharField(_("description"), max_length=300)
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    date = models.DateField(_("date"))
    # Renovations increase ACB (Adjusted Cost Base) for capital gains
    increases_acb = models.BooleanField(
        _("increases cost base"),
        default=False,
        help_text=_("Capital improvements increase the adjusted cost base for tax purposes."),
    )
    paid_by = models.ForeignKey(
        PropertyOwnership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_paid",
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.description} — ${self.amount}"


class PropertyValuation(models.Model):
    """Track valuation history over time."""

    SOURCE_CHOICES = [
        ("manual", _("Manual estimate")),
        ("appraisal", _("Professional appraisal")),
        ("municipal", _("Municipal assessment")),
        ("comparable", _("Comparable sales")),
    ]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="valuations"
    )
    value = models.DecimalField(_("value"), max_digits=12, decimal_places=2)
    date = models.DateField(_("date"))
    source = models.CharField(
        _("source"), max_length=20, choices=SOURCE_CHOICES, default="manual"
    )
    note = models.CharField(_("note"), max_length=300, blank=True)

    class Meta:
        ordering = ["-date"]
```

---

## Core Service Functions

```python
# apps/real_estate/services.py

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

TWO_PLACES = Decimal("0.01")


# ── Amortization ──────────────────────────────────────────────

def calculate_monthly_rate(annual_rate_pct, rate_type="fixed"):
    """Convert nominal annual rate to monthly rate (Canadian rules).

    Fixed: semi-annual compounding (by law).
    Variable: monthly compounding.
    """
    r = annual_rate_pct / 100
    if rate_type == "fixed":
        return (1 + r / 2) ** (Decimal("1") / 6) - 1
    return r / 12


def calculate_monthly_payment(principal, annual_rate_pct, amortization_years,
                               rate_type="fixed"):
    """Monthly payment for a Canadian mortgage."""
    r = calculate_monthly_rate(annual_rate_pct, rate_type)
    n = amortization_years * 12
    if r == 0:
        return (principal / n).quantize(TWO_PLACES)
    pmt = (r * principal) / (1 - (1 + r) ** (-n))
    return pmt.quantize(TWO_PLACES)


def generate_amortization_schedule(mortgage):
    """Full amortization schedule for a mortgage.

    Returns list of dicts:
        payment_number, date, total_payment, principal, interest, balance
    """
    r = calculate_monthly_rate(mortgage.annual_rate, mortgage.rate_type)
    n = mortgage.amortization_years * 12
    principal = mortgage.effective_principal
    pmt = calculate_monthly_payment(
        principal, mortgage.annual_rate, mortgage.amortization_years,
        mortgage.rate_type,
    )

    balance = principal
    schedule = []
    payment_date = mortgage.start_date

    for i in range(1, n + 1):
        interest = (balance * r).quantize(TWO_PLACES)
        principal_portion = pmt - interest

        if balance < principal_portion:
            principal_portion = balance
            actual_payment = interest + principal_portion
        else:
            actual_payment = pmt

        balance = max(balance - principal_portion, Decimal("0"))
        payment_date += relativedelta(months=1)

        schedule.append({
            "payment_number": i,
            "date": payment_date,
            "total_payment": actual_payment,
            "principal": principal_portion,
            "interest": interest,
            "balance": balance,
        })

        if balance == 0:
            break

    return schedule


# ── Mortgage Balance ──────────────────────────────────────────

def get_remaining_balance(mortgage, as_of_date=None):
    """Remaining mortgage balance at a given date."""
    if as_of_date is None:
        as_of_date = date.today()

    schedule = generate_amortization_schedule(mortgage)
    for entry in schedule:
        if entry["date"] >= as_of_date:
            return entry["balance"]

    return Decimal("0")


def get_total_paid(mortgage, as_of_date=None):
    """Total principal and interest paid up to a date."""
    if as_of_date is None:
        as_of_date = date.today()

    schedule = generate_amortization_schedule(mortgage)
    total_principal = Decimal("0")
    total_interest = Decimal("0")

    for entry in schedule:
        if entry["date"] > as_of_date:
            break
        total_principal += entry["principal"]
        total_interest += entry["interest"]

    return {
        "total_principal_paid": total_principal,
        "total_interest_paid": total_interest,
        "total_paid": total_principal + total_interest,
    }


# ── Ownership & Equity ───────────────────────────────────────

def get_current_ownership_shares(property, as_of_date=None):
    """Get active ownership shares for a property at a given date.

    Returns dict: {PropertyOwnership: Decimal(share_pct)}
    """
    if as_of_date is None:
        as_of_date = date.today()

    period = (
        property.ownership_periods
        .filter(start_date__lte=as_of_date)
        .filter(models.Q(end_date__gte=as_of_date) | models.Q(end_date__isnull=True))
        .order_by("-start_date")
        .first()
    )

    if not period:
        # Fallback: equal split among all owners
        ownerships = property.ownerships.all()
        count = ownerships.count()
        if count == 0:
            return {}
        share = (Decimal("100") / count).quantize(TWO_PLACES)
        return {o: share for o in ownerships}

    return {
        share.owner: share.share_pct
        for share in period.shares.select_related("owner__user").all()
    }


def get_owner_contributions(ownership):
    """Total contributions by one owner: down payment + principal paid + expenses."""
    # Down payment
    down = ownership.down_payment

    # Principal from mortgage payments attributed to this owner
    principal_paid = (
        ownership.mortgage_payments
        .aggregate(total=models.Sum("principal_portion"))["total"]
        or Decimal("0")
    )

    # Expenses paid by this owner
    expenses_paid = (
        ownership.expenses_paid
        .aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0")
    )

    return {
        "down_payment": down,
        "principal_paid": principal_paid,
        "expenses_paid": expenses_paid,
        "total": down + principal_paid + expenses_paid,
    }


# ── Sale Simulation ──────────────────────────────────────────

def estimate_sale_proceeds(property, sale_price=None, agent_commission_pct=Decimal("5"),
                            notary_fees=Decimal("800")):
    """Estimate net proceeds if property sold today.

    Returns per-owner breakdown.
    """
    if sale_price is None:
        sale_price = property.current_valuation

    # Remaining mortgage balance
    total_mortgage_balance = Decimal("0")
    for mortgage in property.mortgages.filter(is_active=True):
        total_mortgage_balance += get_remaining_balance(mortgage)

    # Agent commission + taxes (GST 5% + QST 9.975%)
    commission = sale_price * agent_commission_pct / 100
    commission_with_tax = commission * Decimal("1.14975")

    # Capital gains tax (only for non-primary residence)
    capital_gains_tax = Decimal("0")
    if property.usage != "primary":
        acb = _calculate_acb(property)
        capital_gain = sale_price - acb
        if capital_gain > 0:
            # 50% inclusion rate, estimate ~45% combined marginal rate
            capital_gains_tax = capital_gain * Decimal("0.50") * Decimal("0.45")

    # Net proceeds
    gross_equity = sale_price - total_mortgage_balance
    total_costs = commission_with_tax + notary_fees + capital_gains_tax
    net_proceeds = gross_equity - total_costs

    # Split per owner
    shares = get_current_ownership_shares(property)
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

    return {
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


def _calculate_acb(property):
    """Adjusted Cost Base for capital gains calculation."""
    acb = (
        property.purchase_price
        + property.welcome_tax_paid
        + property.notary_fees_purchase
    )
    # Add capital improvements (renovations that increase value)
    capital_improvements = (
        property.expenses
        .filter(increases_acb=True)
        .aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0")
    )
    return acb + capital_improvements


# ── Property Snapshot ─────────────────────────────────────────

def get_property_snapshot(property):
    """Summary metrics for a single property."""
    mortgage_balance = Decimal("0")
    monthly_payment = Decimal("0")
    for mortgage in property.mortgages.filter(is_active=True):
        mortgage_balance += get_remaining_balance(mortgage)
        monthly_payment += mortgage.monthly_payment

    equity = property.current_valuation - mortgage_balance

    return {
        "current_valuation": property.current_valuation,
        "purchase_price": property.purchase_price,
        "appreciation": property.total_appreciation,
        "appreciation_pct": property.total_appreciation_pct,
        "mortgage_balance": mortgage_balance,
        "equity": equity,
        "equity_pct": (
            (equity / property.current_valuation * 100)
            if property.current_valuation else Decimal("0")
        ),
        "monthly_payment": monthly_payment,
    }


def get_owner_snapshot(property, user):
    """Property snapshot from one owner's perspective."""
    ownership = property.ownerships.get(user=user)
    shares = get_current_ownership_shares(property)
    share_pct = shares.get(ownership, Decimal("0"))

    snapshot = get_property_snapshot(property)
    contributions = get_owner_contributions(ownership)

    return {
        "share_pct": share_pct,
        "your_equity": (snapshot["equity"] * share_pct / 100).quantize(TWO_PLACES),
        "your_valuation": (
            snapshot["current_valuation"] * share_pct / 100
        ).quantize(TWO_PLACES),
        "your_mortgage_share": (
            snapshot["mortgage_balance"] * share_pct / 100
        ).quantize(TWO_PLACES),
        "your_contributions": contributions,
        **snapshot,
    }
```

---

## Shared Property Access (Co-Ownership Between Users)

The key feature: two Limpid users who co-own a property should see the same property data.

### How It Works

1. **User A creates a property** → automatically becomes owner with `is_admin=True`
2. **User A invites User B** via email → creates a `PropertyOwnership` for User B
3. Both users see the property in their dashboard
4. Both see the same data (valuation, mortgage, expenses)
5. Each sees their **personal view** (their share, their equity, their contributions)
6. Only `is_admin=True` owners can edit property details

### Invitation Flow

```python
# apps/real_estate/models.py (add)

class PropertyInvitation(models.Model):
    """Pending invitation for a co-owner to join a property."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="invitations"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    email = models.EmailField(_("invitee email"))
    down_payment = models.DecimalField(
        _("down payment"), max_digits=12, decimal_places=2, default=0
    )
    token = models.CharField(max_length=64, unique=True)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

```python
# apps/real_estate/views.py (invitation)

@login_required
def invite_co_owner(request, property_id):
    """Send invitation to a co-owner."""
    prop = get_object_or_404(Property, pk=property_id)
    ownership = get_object_or_404(
        PropertyOwnership, property=prop, user=request.user, is_admin=True
    )

    if request.method == "POST":
        form = InviteCoOwnerForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.property = prop
            invitation.invited_by = request.user
            invitation.token = get_random_string(64)
            invitation.save()
            # Send email with link: /real-estate/invite/{token}/accept/
            send_invitation_email(invitation)
            return redirect("real_estate:detail", pk=prop.pk)

    form = InviteCoOwnerForm()
    return render(request, "real_estate/invite.html", {
        "property": prop, "form": form,
    })


@login_required
def accept_invitation(request, token):
    """Accept a co-ownership invitation."""
    invitation = get_object_or_404(
        PropertyInvitation, token=token, accepted=False
    )

    if request.user.email != invitation.email:
        # Allow if user is logged in with a different email?
        # For now, require matching email
        messages.error(request, _("This invitation is for a different email."))
        return redirect("home")

    PropertyOwnership.objects.create(
        user=request.user,
        property=invitation.property,
        is_admin=False,
        down_payment=invitation.down_payment,
    )
    invitation.accepted = True
    invitation.save()

    return redirect("real_estate:detail", pk=invitation.property.pk)
```

---

## Views

```python
# apps/real_estate/views.py

@login_required
def property_list(request):
    """List all properties the user owns (or co-owns)."""
    properties = Property.objects.filter(owners=request.user)
    summaries = []
    for prop in properties:
        snapshot = get_owner_snapshot(prop, request.user)
        summaries.append({"property": prop, "snapshot": snapshot})

    return render(request, "real_estate/list.html", {
        "summaries": summaries,
    })


@login_required
def property_detail(request, pk):
    """Detailed view of a single property."""
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    ownership = prop.ownerships.get(user=request.user)

    snapshot = get_property_snapshot(prop)
    owner_snapshot = get_owner_snapshot(prop, request.user)
    shares = get_current_ownership_shares(prop)
    sale_estimate = estimate_sale_proceeds(prop)

    # Active mortgage
    active_mortgage = prop.mortgages.filter(is_active=True).first()
    amortization = []
    if active_mortgage:
        amortization = generate_amortization_schedule(active_mortgage)

    expenses = prop.expenses.all()[:20]
    valuations = prop.valuations.all()[:10]

    return render(request, "real_estate/detail.html", {
        "property": prop,
        "ownership": ownership,
        "snapshot": snapshot,
        "owner_snapshot": owner_snapshot,
        "shares": shares,
        "sale_estimate": sale_estimate,
        "mortgage": active_mortgage,
        "amortization": amortization,
        "expenses": expenses,
        "valuations": valuations,
    })


@login_required
def property_create(request):
    """Create a new property."""
    if request.method == "POST":
        form = PropertyForm(request.POST)
        mortgage_form = MortgageForm(request.POST)
        if form.is_valid() and mortgage_form.is_valid():
            prop = form.save()
            # Create ownership for current user
            PropertyOwnership.objects.create(
                user=request.user,
                property=prop,
                is_admin=True,
                down_payment=form.cleaned_data.get("down_payment", 0),
            )
            # Create initial ownership period (100% for creator)
            period = OwnershipPeriod.objects.create(
                property=prop, start_date=prop.purchase_date,
            )
            OwnershipPeriodShare.objects.create(
                period=period,
                owner=prop.ownerships.get(user=request.user),
                share_pct=Decimal("100"),
            )
            # Create mortgage if provided
            if mortgage_form.cleaned_data.get("principal"):
                mortgage = mortgage_form.save(commit=False)
                mortgage.property = prop
                mortgage.save()

            return redirect("real_estate:detail", pk=prop.pk)
    else:
        form = PropertyForm()
        mortgage_form = MortgageForm()

    return render(request, "real_estate/create.html", {
        "form": form,
        "mortgage_form": mortgage_form,
    })


@login_required
def add_expense(request, pk):
    """Add an expense to a property (HTMX partial)."""
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    ownership = prop.ownerships.get(user=request.user)

    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.property = prop
            expense.paid_by = ownership
            expense.save()
            # Return updated expense list (HTMX swap)
            expenses = prop.expenses.all()[:20]
            return render(request, "real_estate/partials/expense_list.html", {
                "expenses": expenses,
            })

    form = ExpenseForm()
    return render(request, "real_estate/partials/expense_form.html", {
        "form": form, "property": prop,
    })


@login_required
def amortization_view(request, pk, mortgage_id):
    """Full amortization schedule view."""
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, property=prop)
    schedule = generate_amortization_schedule(mortgage)
    paid = get_total_paid(mortgage)

    return render(request, "real_estate/amortization.html", {
        "property": prop,
        "mortgage": mortgage,
        "schedule": schedule,
        "paid": paid,
    })


@login_required
def sale_simulator(request, pk):
    """What-if sale price simulator (HTMX)."""
    prop = get_object_or_404(Property, pk=pk, owners=request.user)

    sale_price = request.GET.get("sale_price")
    commission = request.GET.get("commission", "5")

    if sale_price:
        estimate = estimate_sale_proceeds(
            prop,
            sale_price=Decimal(sale_price),
            agent_commission_pct=Decimal(commission),
        )
    else:
        estimate = estimate_sale_proceeds(prop)

    return render(request, "real_estate/partials/sale_estimate.html", {
        "property": prop,
        "estimate": estimate,
    })
```

---

## URL Structure

```python
# apps/real_estate/urls.py

from django.urls import path
from . import views

app_name = "real_estate"

urlpatterns = [
    path("", views.property_list, name="list"),
    path("create/", views.property_create, name="create"),
    path("<int:pk>/", views.property_detail, name="detail"),
    path("<int:pk>/edit/", views.property_edit, name="edit"),
    path("<int:pk>/expense/", views.add_expense, name="add_expense"),
    path("<int:pk>/valuation/", views.add_valuation, name="add_valuation"),
    path("<int:pk>/mortgage/<int:mortgage_id>/amortization/",
         views.amortization_view, name="amortization"),
    path("<int:pk>/sale-simulator/", views.sale_simulator, name="sale_simulator"),
    path("<int:pk>/invite/", views.invite_co_owner, name="invite"),
    path("invite/<str:token>/accept/", views.accept_invitation, name="accept_invite"),
    path("<int:pk>/ownership-periods/", views.manage_ownership_periods,
         name="ownership_periods"),
]

# config/urls.py — add:
path("real-estate/", include("apps.real_estate.urls")),
```

---

## Template Structure

```
templates/real_estate/
├── list.html                    # Property cards with snapshot metrics
├── detail.html                  # Full property dashboard
├── create.html                  # Multi-section form (property + mortgage)
├── edit.html                    # Edit property details
├── amortization.html            # Full amortization schedule table
├── invite.html                  # Invite co-owner form
├── partials/
│   ├── snapshot_card.html       # Property metrics (HTMX refreshable)
│   ├── ownership_card.html      # Owner shares visualization
│   ├── mortgage_card.html       # Mortgage details + mini amortization
│   ├── expense_list.html        # Expense table (HTMX swappable)
│   ├── expense_form.html        # Add expense form (HTMX)
│   ├── sale_estimate.html       # Sale simulation results (HTMX)
│   └── valuation_history.html   # Valuation timeline
```

### Key Template: Property Detail

```django
{# templates/real_estate/detail.html #}
{% extends "base.html" %}
{% load i18n %}

{% block content %}
<div class="container-limpid py-6 space-y-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold text-text">{{ property.name }}</h1>
    {% include "components/badge.html" with label=property.get_usage_display variant="info" %}
  </div>
  <p class="text-text-muted">{{ property.address }}, {{ property.city }}</p>

  {# ── Row 1: Snapshot + Your Share ── #}
  <div class="grid gap-6 md:grid-cols-2">

    {# Property snapshot #}
    {% include "components/card_start.html" with title=_("Property Value") %}
      <p class="text-3xl font-bold text-text">${{ snapshot.current_valuation|floatformat:0 }}</p>
      <div class="mt-4 space-y-2">
        {% include "components/metric_row.html" with label=_("Purchase price") value=snapshot.purchase_price|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Appreciation") value=snapshot.appreciation|floatformat:0 annotation=snapshot.appreciation_pct|floatformat:1 %}
        {% include "components/metric_row.html" with label=_("Mortgage balance") value=snapshot.mortgage_balance|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Equity") value=snapshot.equity|floatformat:0 annotation=snapshot.equity_pct|floatformat:1 %}
      </div>
    {% include "components/card_end.html" %}

    {# Your share #}
    {% include "components/card_start.html" with title=_("Your Share") %}
      <p class="text-lg font-semibold text-primary-600">{{ owner_snapshot.share_pct }}%</p>
      <div class="mt-4 space-y-2">
        {% include "components/metric_row.html" with label=_("Your equity") value=owner_snapshot.your_equity|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Your valuation share") value=owner_snapshot.your_valuation|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Your mortgage share") value=owner_snapshot.your_mortgage_share|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Down payment") value=owner_snapshot.your_contributions.down_payment|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Principal paid") value=owner_snapshot.your_contributions.principal_paid|floatformat:0 %}
      </div>
    {% include "components/card_end.html" %}

  </div>

  {# ── Row 2: Ownership split + Mortgage ── #}
  <div class="grid gap-6 md:grid-cols-2">

    {# Co-owners #}
    {% include "components/card_start.html" with title=_("Ownership") %}
      <div class="space-y-3">
        {% for ownership, share in shares.items %}
        <div class="flex items-center justify-between">
          <span class="text-text">{{ ownership.user.get_full_name|default:ownership.user.email }}</span>
          <span class="font-semibold text-primary-600">{{ share }}%</span>
        </div>
        {% endfor %}
      </div>
      {% if ownership.is_admin %}
      <div class="mt-4 pt-4 border-t border-border">
        <a href="{% url 'real_estate:invite' property.pk %}"
           class="text-sm text-primary-600 hover:text-primary-700">
          {% trans "Invite co-owner" %}
        </a>
      </div>
      {% endif %}
    {% include "components/card_end.html" %}

    {# Mortgage summary #}
    {% if mortgage %}
    {% include "components/card_start.html" with title=_("Mortgage") %}
      <div class="space-y-2">
        {% include "components/metric_row.html" with label=_("Lender") value=mortgage.lender %}
        {% include "components/metric_row.html" with label=_("Rate") value=mortgage.annual_rate|floatformat:2 annotation=mortgage.get_rate_type_display %}
        {% include "components/metric_row.html" with label=_("Monthly payment") value=snapshot.monthly_payment|floatformat:2 %}
        {% include "components/metric_row.html" with label=_("Remaining balance") value=snapshot.mortgage_balance|floatformat:0 %}
        {% include "components/metric_row.html" with label=_("Amortization") value=mortgage.amortization_years annotation=_("years") %}
      </div>
      <div class="mt-4 pt-4 border-t border-border">
        <a href="{% url 'real_estate:amortization' property.pk mortgage.pk %}"
           class="text-sm text-primary-600 hover:text-primary-700">
          {% trans "View full amortization schedule" %} →
        </a>
      </div>
    {% include "components/card_end.html" %}
    {% endif %}

  </div>

  {# ── Row 3: Sale simulator ── #}
  {% include "components/card_start.html" with title=_("If I sell today...") %}
    <div x-data="{ salePrice: '{{ property.current_valuation }}', commission: '5' }">
      <div class="flex gap-4 mb-4">
        <div>
          <label class="text-sm text-text-muted">{% trans "Sale price" %}</label>
          <input type="number" x-model="salePrice"
                 class="mt-1 block w-full rounded-md border-border px-3 py-2 text-sm"
                 hx-get="{% url 'real_estate:sale_simulator' property.pk %}"
                 hx-trigger="input changed delay:500ms"
                 hx-target="#sale-results"
                 hx-include="[name='commission']"
                 name="sale_price" />
        </div>
        <div>
          <label class="text-sm text-text-muted">{% trans "Agent commission (%)" %}</label>
          <input type="number" x-model="commission" step="0.5" min="0" max="10"
                 class="mt-1 block w-full rounded-md border-border px-3 py-2 text-sm"
                 name="commission" />
        </div>
      </div>
      <div id="sale-results">
        {% include "real_estate/partials/sale_estimate.html" %}
      </div>
    </div>
  {% include "components/card_end.html" %}

  {# ── Row 4: Expenses ── #}
  {% include "components/card_start.html" with title=_("Expenses & Renovations") %}
    <div id="expense-list">
      {% include "real_estate/partials/expense_list.html" %}
    </div>
    {% if ownership.is_admin %}
    <div class="mt-4 pt-4 border-t border-border">
      <button hx-get="{% url 'real_estate:add_expense' property.pk %}"
              hx-target="#expense-form-container"
              class="text-sm text-primary-600 hover:text-primary-700">
        {% trans "+ Add expense" %}
      </button>
      <div id="expense-form-container"></div>
    </div>
    {% endif %}
  {% include "components/card_end.html" %}

</div>
{% endblock %}
```

---

## Navigation Integration

```python
# config/context_processors.py — add to nav_current():
elif path.startswith("/real-estate"):
    section = "real_estate"
```

Add to sidebar and bottom nav:
```django
{# In templates/components/nav.html — add after portfolios #}
<a href="{% url 'real_estate:list' %}"
   class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm
          {% if nav_current == 'real_estate' %}bg-primary-50 text-primary-700 font-medium{% else %}text-text-muted hover:bg-gray-50 hover:text-text{% endif %}">
  <svg class="h-5 w-5" ...><!-- house icon --></svg>
  {% trans "Real Estate" %}
</a>
```

---

## Files to Create / Modify

### New Files
| File | Description |
|------|-------------|
| `apps/real_estate/__init__.py` | App init |
| `apps/real_estate/apps.py` | App config |
| `apps/real_estate/models.py` | All models (Property, Mortgage, etc.) |
| `apps/real_estate/services.py` | Business logic (amortization, equity, sale sim) |
| `apps/real_estate/views.py` | All views |
| `apps/real_estate/urls.py` | URL routing |
| `apps/real_estate/forms.py` | Property, Mortgage, Expense, Invitation forms |
| `apps/real_estate/admin.py` | Admin registration |
| `apps/real_estate/migrations/` | Auto-generated migrations |
| `apps/real_estate/tests/test_models.py` | Model tests |
| `apps/real_estate/tests/test_services.py` | Amortization & calculation tests |
| `apps/real_estate/tests/test_views.py` | View tests |
| `templates/real_estate/list.html` | Property list page |
| `templates/real_estate/detail.html` | Property detail/dashboard |
| `templates/real_estate/create.html` | Create property form |
| `templates/real_estate/edit.html` | Edit property form |
| `templates/real_estate/amortization.html` | Full amortization schedule |
| `templates/real_estate/invite.html` | Invite co-owner |
| `templates/real_estate/partials/*.html` | HTMX partial templates |

### Files to Modify
| File | Change |
|------|--------|
| `config/settings/base.py` | Add `"apps.real_estate"` to INSTALLED_APPS |
| `config/urls.py` | Add `path("real-estate/", include("apps.real_estate.urls"))` |
| `config/context_processors.py` | Add `real_estate` section to `nav_current` |
| `templates/components/nav.html` | Add Real Estate nav item |
| `templates/components/bottom_nav.html` | Add Real Estate nav item (replace one existing or use "More" menu) |
| `pyproject.toml` | Add `python-dateutil` dependency (for `relativedelta`) |
| `locale/fr/LC_MESSAGES/django.po` | French translations for all new strings |

---

## Implementation Order

### Phase 1: Core Models & Amortization (Week 1)
1. Create `apps/real_estate/` app scaffold
2. Implement all models
3. Implement amortization calculation service
4. Write tests for amortization math
5. Admin registration
6. Migrations

### Phase 2: Property CRUD & Dashboard (Week 2)
1. Property create/edit forms
2. Property list and detail views
3. Property snapshot service
4. Templates (list, detail, create)
5. Navigation integration

### Phase 3: Ownership & Co-ownership (Week 3)
1. Ownership periods and share management
2. Invitation flow (create, email, accept)
3. Owner-specific views (your share, your contributions)
4. Permission checks (is_admin for edits)

### Phase 4: Sale Simulator & Expenses (Week 4)
1. Sale proceeds estimation
2. HTMX sale price simulator
3. Expense tracking (add, list)
4. Valuation history

### Phase 5: Polish & i18n (Week 5)
1. French translations
2. Mobile responsive testing
3. Edge cases (single owner, no mortgage, etc.)
4. Full test coverage

---

## Verification Plan

1. **Unit tests**: Amortization math (known inputs → expected outputs), ownership splits, sale proceeds
2. **Integration tests**: Create property → add mortgage → view detail → invite co-owner → accept → both see same data
3. **Manual testing**:
   - Create a property with $500k value, $400k mortgage at 5%, 25 years
   - Verify monthly payment matches online calculator
   - Add a co-owner with 50/50 split, then change to 75/25
   - Simulate sale and verify per-owner proceeds
   - Test on mobile (bottom nav, responsive cards)
4. **Lint/format**: `uv run ruff check . && uv run ruff format --check .`
5. **Full test suite**: `uv run pytest`

---

## Dependency Addition

```toml
# pyproject.toml — add to [project.dependencies]:
"python-dateutil>=2.9",
```

Required for `relativedelta` in amortization date calculations.

---

## Detailed Todo List

### Phase 1: App Scaffold & Core Models ✅

- [x] **1.1** Add `python-dateutil>=2.9` to `pyproject.toml` dependencies
- [x] **1.2** Run `uv sync` to install the new dependency
- [x] **1.3** Create the `apps/real_estate/` app directory with all files
- [x] **1.4** Add `"apps.real_estate"` to `INSTALLED_APPS` in `config/settings/base.py`
- [x] **1.5** Implement `Property` model with all fields
- [x] **1.6** Implement `PropertyOwnership` model
- [x] **1.7** Implement `OwnershipPeriod` model
- [x] **1.8** Implement `OwnershipPeriodShare` model
- [x] **1.9** Implement `Mortgage` model (FK renamed to `real_estate` to avoid shadowing Python's `@property`)
- [x] **1.10** Implement `MortgagePayment` model
- [x] **1.11** Implement `PropertyExpense` model
- [x] **1.12** Implement `PropertyValuation` model
- [x] **1.13** Implement `PropertyInvitation` model
- [x] **1.14** Run `makemigrations real_estate`
- [x] **1.15** Run `migrate`
- [x] **1.16** Register all models in `admin.py`

### Phase 2: Amortization & Core Services ✅

- [x] **2.1–2.5** Implement all amortization service functions
- [x] **2.6–2.12** Write all amortization tests
- [x] **2.13** All amortization tests pass (54 total)

### Phase 3: Property Snapshot & Ownership Services ✅

- [x] **3.1–3.4** Implement all snapshot and ownership service functions
- [x] **3.5–3.9** Write all snapshot/ownership tests
- [x] **3.10** All tests pass

### Phase 4: Sale Simulation Services ✅

- [x] **4.1–4.2** Implement ACB calculation and sale proceeds estimation
- [x] **4.3–4.7** Write all sale simulation tests
- [x] **4.8** All tests pass

### Phase 5: Forms ✅

- [x] **5.1** PropertyForm with down_payment extra field
- [x] **5.2** MortgageForm (all fields optional)
- [x] **5.3** ExpenseForm
- [x] **5.4** ValuationForm
- [x] **5.5** InviteCoOwnerForm
- [x] **5.6** Ownership period management via view (simplified from formset)

### Phase 6: Views — Property CRUD ✅

- [x] **6.1–6.4** All CRUD views implemented
- [x] **6.5–6.9** All view tests written and passing

### Phase 7: Views — Expenses, Valuations, Amortization ✅

- [x] **7.1–7.4** All views implemented (add_expense, add_valuation, amortization_view, sale_simulator)
- [x] **7.5–7.6** Tests written and passing

### Phase 8: Views — Co-ownership & Invitations ✅

- [x] **8.1** invite_co_owner view
- [x] **8.2** accept_invitation view
- [x] **8.3** manage_ownership_periods view
- [x] **8.4** Invitation creates token (email sending deferred to later)
- [x] **8.5–8.9** All invitation tests written and passing

### Phase 9: URL Routing & Navigation ✅

- [x] **9.1–9.5** All URL patterns, config/urls.py, context processor, sidebar and bottom nav
- [x] **9.6** Active state verified

### Phase 10: Templates — Property List & Create ✅

- [x] **10.1** list.html — property cards grid
- [x] **10.2** create.html — multi-section form
- [x] **10.3** edit.html — pre-populated form

### Phase 11: Templates — Property Detail Dashboard ✅

- [x] **11.1–11.6** Full detail.html with all 5 rows

### Phase 12: Templates — Partials (HTMX) ✅

- [x] **12.1** sale_estimate.html
- [x] **12.2** expense_list.html
- [x] **12.3** expense_form.html
- [x] **12.4** valuation_history.html
- [x] valuation_form.html (bonus)

### Phase 13: Templates — Amortization & Invitation ✅

- [x] **13.1** amortization.html — full schedule table with summary stats
- [x] **13.2** invite.html — invite co-owner form
- [x] ownership_periods.html (bonus)

### Phase 14: Internationalization (i18n) ✅

- [x] **14.1** All model verbose_name / help_text use `gettext_lazy`
- [x] **14.2** All template strings use `{% trans %}`
- [x] **14.3** Ran `makemessages -l fr`
- [x] **14.4** All new strings translated in `django.po` (100+ real estate strings)
- [x] **14.5** Ran `compilemessages`

### Phase 15: Edge Cases & Defensive Code ✅

- [x] **15.1** Property with no mortgage handled (conditional `{% if mortgage %}` in detail.html)
- [x] **15.2** Single owner handled (100% share, ownership card still shows)
- [x] **15.3** No ownership periods fallback to equal split (in `get_current_ownership_shares`)
- [x] **15.4** 0% rate handled (division by zero guard in `calculate_monthly_payment`)
- [x] **15.5** Sale simulation with any price handled (Decimal parsing with InvalidOperation catch)
- [x] **15.6** Share validation deferred to period management form (future)
- [x] **15.7** Duplicate invitation prevention deferred (future)
- [x] **15.8** Invitation email mismatch shows error message

### Phase 16: Final Verification ✅

- [x] **16.1** `ruff check .` — All checks passed
- [x] **16.2** `ruff format --check .` — All files formatted
- [x] **16.3** `pytest` — 86 tests pass (32 existing + 54 new)
- [x] **16.4** `makemigrations --check` — No pending migrations
- [x] **16.5–16.13** Manual testing deferred to user

### Phase 17: CLAUDE.md & Documentation Update ✅

- [x] **17.1** Added `apps/real_estate/` to Project Structure
- [x] **17.2** Added `/real-estate/` to URL Patterns table
- [x] **17.3** Updated Completed Milestones
- [x] **17.4** Gotcha: `property` FK field renamed to `real_estate` in Mortgage to avoid shadowing Python's `@property` decorator
