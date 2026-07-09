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
    annual_rate = mortgage.annual_rate
    rate_type = mortgage.rate_type
    n_total = mortgage.amortization_years * 12
    balance = mortgage.effective_principal
    start = mortgage.start_date

    rate_changes = list(mortgage.rate_changes.order_by("effective_date"))
    change_idx = 0

    r = calculate_monthly_rate(annual_rate, rate_type, country)
    insurance_monthly = Decimal("0")
    if mortgage.borrower_insurance_rate:
        insurance_monthly = (mortgage.effective_principal * mortgage.borrower_insurance_rate / 100 / 12).quantize(
            TWO_PLACES
        )

    if r == 0:
        pmt = (balance / n_total).quantize(TWO_PLACES)
    else:
        pmt = ((r * balance) / (1 - (1 + r) ** (-n_total))).quantize(TWO_PLACES)

    schedule = []
    for i in range(1, n_total + 1):
        payment_date = start + relativedelta(months=i)

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
                pmt = (balance / remaining).quantize(TWO_PLACES)
            else:
                pmt = ((r * balance) / (1 - (1 + r) ** (-remaining))).quantize(TWO_PLACES)

        interest = (balance * r).quantize(TWO_PLACES)
        principal_portion = pmt - interest

        if principal_portion >= balance or balance - principal_portion < TWO_PLACES:
            principal_portion = balance
            pmt = principal_portion + interest

        balance = max(balance - principal_portion, Decimal("0"))

        schedule.append(
            {
                "payment_number": i,
                "date": payment_date,
                "total_payment": pmt + insurance_monthly,
                "principal": principal_portion,
                "interest": interest,
                "insurance": insurance_monthly,
                "balance": balance,
                "annual_rate": annual_rate,
            }
        )

        if balance == 0:
            break

    if schedule and schedule[-1]["balance"] > 0:
        last = schedule[-1]
        leftover = last["balance"]
        interest = (leftover * r).quantize(TWO_PLACES)
        payment_date = start + relativedelta(months=last["payment_number"] + 1)
        schedule.append(
            {
                "payment_number": last["payment_number"] + 1,
                "date": payment_date,
                "total_payment": leftover + interest + insurance_monthly,
                "principal": leftover,
                "interest": interest,
                "insurance": insurance_monthly,
                "balance": Decimal("0"),
                "annual_rate": annual_rate,
            }
        )

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


def get_ownership_comparison(prop):
    """Per-owner breakdown: purchase share (down payment ratio) vs contribution share."""
    ownerships = prop.ownerships.select_related("user").all()
    admin_shares = get_current_ownership_shares(prop)

    # At-purchase: ratio of down payments
    total_down = sum(o.down_payment for o in ownerships) or Decimal("1")

    # At-end: ratio of total contributions (down payment + principal paid + expenses)
    contributions = {}
    grand_total = Decimal("0")
    for ownership in ownerships:
        contribs = get_owner_contributions(ownership)
        # Override principal_paid from amortization (same pattern as get_owner_snapshot)
        total_principal = Decimal("0")
        for mortgage in prop.mortgages.filter(is_active=True):
            paid = get_total_paid(mortgage)
            pct = admin_shares.get(ownership, Decimal("0"))
            total_principal += paid["total_principal_paid"] * pct / 100
        contribs["principal_paid"] = total_principal.quantize(TWO_PLACES)
        contribs["total"] = contribs["down_payment"] + contribs["principal_paid"] + contribs["expenses_paid"]
        contributions[ownership] = contribs
        grand_total += contribs["total"]

    if grand_total == 0:
        grand_total = Decimal("1")

    result = []
    for ownership in ownerships:
        c = contributions[ownership]
        result.append(
            {
                "user": ownership.user,
                "ownership": ownership,
                "admin_share": admin_shares.get(ownership, Decimal("0")),
                "purchase_share": (ownership.down_payment / total_down * 100).quantize(TWO_PLACES),
                "contribution_share": (c["total"] / grand_total * 100).quantize(TWO_PLACES),
            }
        )
    return result


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

    valuation = prop.current_valuation or Decimal("0")
    equity = valuation - mortgage_balance
    return {
        "current_valuation": valuation,
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


def calculate_monthly_cost(prop, for_user=None):
    """Calculate the total monthly cost of owning a property."""
    import datetime

    from .models import OwnerMonthlyPayment, RentalIncome

    mortgage_payment = Decimal("0")
    for m in prop.mortgages.filter(is_active=True):
        mortgage_payment += m.monthly_payment

    latest_year = prop.taxes.aggregate(max_year=models.Max("year"))["max_year"]
    taxes_annual = Decimal("0")
    if latest_year:
        taxes_annual = sum(t.amount for t in prop.taxes.filter(year=latest_year))
    taxes_monthly = (taxes_annual / 12).quantize(TWO_PLACES)

    recurring_types = {"condo_fees", "charges_copro", "insurance"}
    one_year_ago = datetime.date.today() - datetime.timedelta(days=365)
    recurring_total = prop.expenses.filter(expense_type__in=recurring_types, date__gte=one_year_ago).aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0")
    recurring_monthly = (recurring_total / 12).quantize(TWO_PLACES)

    rental_income = Decimal("0")
    rental_net = Decimal("0")
    active_rental = RentalIncome.objects.filter(real_estate=prop, end_date__isnull=True).order_by("-start_date").first()
    if not active_rental:
        active_rental = RentalIncome.objects.filter(real_estate=prop).order_by("-start_date").first()
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

    if for_user:
        ownership = prop.ownerships.filter(user=for_user).first()
        if ownership:
            shares = get_current_ownership_shares(prop)
            share_pct = shares.get(ownership, Decimal("100")) / 100
            all_ownerships = list(prop.ownerships.all())

            your_mortgage = Decimal("0")
            for m in prop.mortgages.filter(is_active=True):
                # Collect all custom payments for this mortgage
                customs = {}
                for o in all_ownerships:
                    custom = (
                        OwnerMonthlyPayment.objects.filter(
                            mortgage=m, owner=o, effective_date__lte=datetime.date.today()
                        )
                        .order_by("-effective_date")
                        .first()
                    )
                    if custom:
                        customs[o] = custom.monthly_amount

                if ownership in customs:
                    your_mortgage += customs[ownership]
                else:
                    remainder = m.monthly_payment - sum(customs.values())
                    non_custom_owners = [o for o in all_ownerships if o not in customs]
                    non_custom_share_total = sum(shares.get(o, Decimal("0")) / 100 for o in non_custom_owners)
                    if non_custom_share_total > 0:
                        your_mortgage += (remainder * share_pct / non_custom_share_total).quantize(TWO_PLACES)

            your_taxes = (taxes_monthly * share_pct).quantize(TWO_PLACES)
            your_recurring = (recurring_monthly * share_pct).quantize(TWO_PLACES)
            your_rental_offset = (rental_net * share_pct).quantize(TWO_PLACES)
            your_total = (your_mortgage + your_taxes + your_recurring - your_rental_offset).quantize(TWO_PLACES)

            result["your_mortgage_payment"] = your_mortgage
            result["your_taxes_monthly"] = your_taxes
            result["your_recurring_monthly"] = your_recurring
            result["your_rental_offset"] = your_rental_offset
            result["your_total_monthly"] = your_total

    return result


def generate_per_owner_amortization(mortgage):
    """Generate amortization schedule with per-owner payment breakdown."""
    from .models import OwnerMonthlyPayment

    schedule = generate_amortization_schedule(mortgage)
    prop = mortgage.real_estate
    all_ownerships = list(prop.ownerships.select_related("user").all())

    if len(all_ownerships) < 2:
        return schedule, []

    # Pre-fetch all ownership periods to avoid N+1
    periods = list(prop.ownership_periods.prefetch_related("shares__owner__user").order_by("start_date").all())

    # Pre-fetch all custom payments per owner, keyed by (owner_id, effective_date)
    all_custom_payments = list(OwnerMonthlyPayment.objects.filter(mortgage=mortgage).order_by("effective_date"))

    def get_shares_for_date(as_of_date):
        """Get ownership shares for a specific date from pre-fetched periods."""
        matching = None
        for p in periods:
            if p.start_date <= as_of_date and (p.end_date is None or p.end_date >= as_of_date):
                matching = p
        if matching:
            return {s.owner: s.share_pct for s in matching.shares.all()}
        count = len(all_ownerships)
        if count == 0:
            return {}
        share = (Decimal("100") / count).quantize(TWO_PLACES)
        return {o: share for o in all_ownerships}

    def get_custom_payment_for(owner, as_of_date):
        """Get the latest custom payment for an owner effective on or before as_of_date."""
        result = None
        for cp in all_custom_payments:
            if cp.owner_id == owner.pk and cp.effective_date <= as_of_date:
                result = cp
        return result

    owner_totals = {
        o.pk: {"principal": Decimal("0"), "interest": Decimal("0"), "total": Decimal("0")} for o in all_ownerships
    }

    for entry in schedule:
        payment_date = entry["date"]
        shares = get_shares_for_date(payment_date)
        total_payment = entry["total_payment"]  # includes insurance

        # Collect custom payments
        customs = {}
        for o in all_ownerships:
            cp = get_custom_payment_for(o, payment_date)
            if cp:
                customs[o] = cp.monthly_amount

        remainder = max(total_payment - sum(customs.values()), Decimal("0"))
        non_custom = [o for o in all_ownerships if o not in customs]
        non_custom_share_total = sum(shares.get(o, Decimal("0")) / 100 for o in non_custom)

        owner_payments = {}
        for o in all_ownerships:
            share_pct = shares.get(o, Decimal("0")) / 100
            if o in customs:
                ratio = customs[o] / total_payment if total_payment else Decimal("0")
            elif non_custom_share_total > 0:
                ratio = (
                    (remainder * share_pct / non_custom_share_total) / total_payment if total_payment else Decimal("0")
                )
            else:
                ratio = Decimal("0")

            o_payment = (total_payment * ratio).quantize(TWO_PLACES)
            o_principal = (entry["principal"] * ratio).quantize(TWO_PLACES)
            o_interest = (entry["interest"] * ratio).quantize(TWO_PLACES)
            owner_payments[o.pk] = {
                "owner": o,
                "payment": o_payment,
                "principal": o_principal,
                "interest": o_interest,
            }
            owner_totals[o.pk]["principal"] += o_principal
            owner_totals[o.pk]["interest"] += o_interest
            owner_totals[o.pk]["total"] += o_payment

        entry["owner_payments"] = owner_payments

    owner_summaries = []
    for o in all_ownerships:
        totals = owner_totals[o.pk]
        grand_total = sum(t["total"] for t in owner_totals.values())
        contribution_pct = (totals["total"] / grand_total * 100).quantize(TWO_PLACES) if grand_total else Decimal("0")
        owner_summaries.append(
            {
                "owner": o,
                "principal_paid": totals["principal"],
                "interest_paid": totals["interest"],
                "total_paid": totals["total"],
                "contribution_pct": contribution_pct,
            }
        )

    return schedule, owner_summaries


def generate_evolution_chart_data(mortgage):
    """Generate time series data for amortization evolution line charts."""
    schedule = generate_amortization_schedule(mortgage)
    today = date.today()
    current_label = today.strftime("%Y-%m")
    labels = []
    principal_series = []
    interest_series = []
    balance_series = []
    payment_series = []
    current_month_index = None

    for i, entry in enumerate(schedule):
        label = entry["date"].strftime("%Y-%m")
        labels.append(label)
        principal_series.append(float(entry["principal"]))
        interest_series.append(float(entry["interest"]))
        balance_series.append(float(entry["balance"]))
        payment_series.append(float(entry["total_payment"]))
        if label == current_label:
            current_month_index = i

    return {
        "labels": labels,
        "principal_series": principal_series,
        "interest_series": interest_series,
        "balance_series": balance_series,
        "payment_series": payment_series,
        "current_month_index": current_month_index,
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
