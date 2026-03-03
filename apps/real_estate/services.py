from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models

TWO_PLACES = Decimal("0.01")


# ── Amortization ──────────────────────────────────────────────


def calculate_monthly_rate(annual_rate_pct, rate_type="fixed"):
    r = annual_rate_pct / 100
    if rate_type == "fixed":
        return (1 + r / 2) ** (Decimal("1") / 6) - 1
    return r / 12


def calculate_monthly_payment(principal, annual_rate_pct, amortization_years, rate_type="fixed"):
    r = calculate_monthly_rate(annual_rate_pct, rate_type)
    n = amortization_years * 12
    if r == 0:
        return (principal / n).quantize(TWO_PLACES)
    pmt = (r * principal) / (1 - (1 + r) ** (-n))
    return pmt.quantize(TWO_PLACES)


def generate_amortization_schedule(mortgage):
    r = calculate_monthly_rate(mortgage.annual_rate, mortgage.rate_type)
    n = mortgage.amortization_years * 12
    principal = mortgage.effective_principal
    pmt = calculate_monthly_payment(principal, mortgage.annual_rate, mortgage.amortization_years, mortgage.rate_type)

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
        payment_date = mortgage.start_date + relativedelta(months=i)

        schedule.append(
            {
                "payment_number": i,
                "date": payment_date,
                "total_payment": actual_payment,
                "principal": principal_portion,
                "interest": interest,
                "balance": balance,
            }
        )

        if balance == 0:
            break

    return schedule


# ── Mortgage Balance ──────────────────────────────────────────


def get_remaining_balance(mortgage, as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today()
    schedule = generate_amortization_schedule(mortgage)
    for entry in schedule:
        if entry["date"] >= as_of_date:
            return entry["balance"]
    return Decimal("0")


def get_total_paid(mortgage, as_of_date=None):
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


def get_current_ownership_shares(prop, as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today()

    period = (
        prop.ownership_periods.filter(start_date__lte=as_of_date)
        .filter(models.Q(end_date__gte=as_of_date) | models.Q(end_date__isnull=True))
        .order_by("-start_date")
        .first()
    )

    if not period:
        ownerships = prop.ownerships.all()
        count = ownerships.count()
        if count == 0:
            return {}
        share = (Decimal("100") / count).quantize(TWO_PLACES)
        return {o: share for o in ownerships}

    return {share.owner: share.share_pct for share in period.shares.select_related("owner__user").all()}


def get_owner_contributions(ownership):
    down = ownership.down_payment
    principal_paid = ownership.mortgage_payments.aggregate(total=models.Sum("principal_portion"))["total"] or Decimal(
        "0"
    )
    expenses_paid = ownership.expenses_paid.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    return {
        "down_payment": down,
        "principal_paid": principal_paid,
        "expenses_paid": expenses_paid,
        "total": down + principal_paid + expenses_paid,
    }


# ── Sale Simulation ──────────────────────────────────────────


def estimate_sale_proceeds(prop, sale_price=None, agent_commission_pct=Decimal("5"), notary_fees=Decimal("800")):
    if sale_price is None:
        sale_price = prop.current_valuation

    total_mortgage_balance = Decimal("0")
    for mortgage in prop.mortgages.filter(is_active=True):
        total_mortgage_balance += get_remaining_balance(mortgage)

    commission = sale_price * agent_commission_pct / 100
    commission_with_tax = commission * Decimal("1.14975")

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
        per_owner.append(
            {
                "user": ownership.user,
                "share_pct": share_pct,
                "net_proceeds": owner_share.quantize(TWO_PLACES),
                "contributions": contributions,
            }
        )

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


def _calculate_acb(prop):
    acb = prop.purchase_price + prop.welcome_tax_paid + prop.notary_fees_purchase
    capital_improvements = prop.expenses.filter(increases_acb=True).aggregate(total=models.Sum("amount"))[
        "total"
    ] or Decimal("0")
    return acb + capital_improvements


# ── Property Snapshot ─────────────────────────────────────────


def get_property_snapshot(prop):
    mortgage_balance = Decimal("0")
    monthly_payment = Decimal("0")
    for mortgage in prop.mortgages.filter(is_active=True):
        mortgage_balance += get_remaining_balance(mortgage)
        monthly_payment += mortgage.monthly_payment

    equity = prop.current_valuation - mortgage_balance
    return {
        "current_valuation": prop.current_valuation,
        "purchase_price": prop.purchase_price,
        "appreciation": prop.total_appreciation,
        "appreciation_pct": prop.total_appreciation_pct,
        "mortgage_balance": mortgage_balance,
        "equity": equity,
        "equity_pct": (equity / prop.current_valuation * 100) if prop.current_valuation else Decimal("0"),
        "monthly_payment": monthly_payment.quantize(TWO_PLACES),
    }


def get_owner_snapshot(prop, user):
    ownership = prop.ownerships.get(user=user)
    shares = get_current_ownership_shares(prop)
    share_pct = shares.get(ownership, Decimal("0"))
    snapshot = get_property_snapshot(prop)
    contributions = get_owner_contributions(ownership)

    # Override principal_paid from amortization schedule (MortgagePayment records are rarely created)
    total_principal_paid = Decimal("0")
    for mortgage in prop.mortgages.filter(is_active=True):
        paid = get_total_paid(mortgage)
        total_principal_paid += paid["total_principal_paid"]
    contributions["principal_paid"] = (total_principal_paid * share_pct / 100).quantize(TWO_PLACES)
    contributions["total"] = (
        contributions["down_payment"] + contributions["principal_paid"] + contributions["expenses_paid"]
    )

    return {
        "share_pct": share_pct,
        "your_equity": (snapshot["equity"] * share_pct / 100).quantize(TWO_PLACES),
        "your_valuation": (snapshot["current_valuation"] * share_pct / 100).quantize(TWO_PLACES),
        "your_mortgage_share": (snapshot["mortgage_balance"] * share_pct / 100).quantize(TWO_PLACES),
        "your_contributions": contributions,
        **snapshot,
    }


# ── Notifications ────────────────────────────────────────────


def notify_co_owners(prop, actor, verb, description):
    from .models import PropertyNotification

    co_owners = prop.ownerships.exclude(user=actor).select_related("user")
    notifications = [
        PropertyNotification(
            recipient=ownership.user,
            property=prop,
            actor=actor,
            verb=verb,
            description=description,
        )
        for ownership in co_owners
    ]
    PropertyNotification.objects.bulk_create(notifications)
