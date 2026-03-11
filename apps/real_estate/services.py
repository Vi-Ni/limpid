from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models

TWO_PLACES = Decimal("0.01")


# ── Amortization ──────────────────────────────────────────────


def calculate_monthly_rate(annual_rate_pct, rate_type="fixed", country="CA"):
    r = annual_rate_pct / 100
    if country == "FR":
        return r / 12
    if rate_type == "fixed":
        return (1 + r / 2) ** (Decimal("1") / 6) - 1
    return r / 12


def calculate_monthly_payment(principal, annual_rate_pct, amortization_years, rate_type="fixed", country="CA"):
    r = calculate_monthly_rate(annual_rate_pct, rate_type, country)
    n = amortization_years * 12
    if r == 0:
        return (principal / n).quantize(TWO_PLACES)
    pmt = (r * principal) / (1 - (1 + r) ** (-n))
    return pmt.quantize(TWO_PLACES)


def generate_amortization_schedule(mortgage):
    country = mortgage.real_estate.country
    r = calculate_monthly_rate(mortgage.annual_rate, mortgage.rate_type, country)
    n = mortgage.amortization_years * 12
    principal = mortgage.effective_principal
    pmt = calculate_monthly_payment(
        principal, mortgage.annual_rate, mortgage.amortization_years, mortgage.rate_type, country
    )

    insurance_monthly = Decimal("0")
    if mortgage.borrower_insurance_rate:
        insurance_monthly = (mortgage.effective_principal * mortgage.borrower_insurance_rate / 100 / 12).quantize(
            TWO_PLACES
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
        payment_date = mortgage.start_date + relativedelta(months=i)

        schedule.append(
            {
                "payment_number": i,
                "date": payment_date,
                "total_payment": actual_payment + insurance_monthly,
                "principal": principal_portion,
                "interest": interest,
                "insurance": insurance_monthly,
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


def estimate_sale_proceeds(prop, sale_price=None, agent_commission_pct=None, notary_fees=None):
    if sale_price is None:
        sale_price = prop.current_valuation

    if prop.country == "FR":
        if agent_commission_pct is None:
            agent_commission_pct = Decimal("5")
        if notary_fees is None:
            notary_fees = Decimal("3000")
    else:
        if agent_commission_pct is None:
            agent_commission_pct = Decimal("5")
        if notary_fees is None:
            notary_fees = Decimal("800")

    total_mortgage_balance = Decimal("0")
    for mortgage in prop.mortgages.filter(is_active=True):
        total_mortgage_balance += get_remaining_balance(mortgage)

    commission = sale_price * agent_commission_pct / 100
    commission_with_tax = commission * Decimal("1.20") if prop.country == "FR" else commission * Decimal("1.14975")

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
        per_owner.append(
            {
                "user": ownership.user,
                "share_pct": share_pct,
                "net_proceeds": owner_share.quantize(TWO_PLACES),
                "contributions": contributions,
            }
        )

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


def _calculate_acb(prop):
    acb = prop.purchase_price + prop.welcome_tax_paid + prop.notary_fees_purchase
    capital_improvements = prop.expenses.filter(increases_acb=True).aggregate(total=models.Sum("amount"))[
        "total"
    ] or Decimal("0")
    return acb + capital_improvements


def _calculate_french_capital_gains_tax(prop, sale_price):
    if prop.usage == "primary":
        return Decimal("0"), {}

    acb = _calculate_acb(prop)
    raw_gain = sale_price - acb
    if raw_gain <= 0:
        return Decimal("0"), {}

    today = date.today()
    holding_years = (today - prop.purchase_date).days // 365

    if holding_years >= 22:
        ir_abatement_pct = Decimal("100")
    elif holding_years <= 5:
        ir_abatement_pct = Decimal("0")
    elif holding_years == 21:
        ir_abatement_pct = Decimal("96")
    else:
        ir_abatement_pct = Decimal(str((holding_years - 5) * 6))

    if holding_years >= 30:
        ps_abatement_pct = Decimal("100")
    elif holding_years <= 5:
        ps_abatement_pct = Decimal("0")
    elif holding_years <= 21:
        ps_abatement_pct = Decimal(str(Decimal(str(holding_years - 5)) * Decimal("1.65")))
    elif holding_years == 22:
        ps_abatement_pct = Decimal("28")
    else:
        ps_abatement_pct = Decimal("28") + Decimal(str((holding_years - 22) * 9))

    ir_taxable = raw_gain * (1 - ir_abatement_pct / 100)
    ps_taxable = raw_gain * (1 - ps_abatement_pct / 100)

    ir_tax = ir_taxable * Decimal("0.19")
    ps_tax = ps_taxable * Decimal("0.172")

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
