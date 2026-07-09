import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from .forms import (
    ExpenseForm,
    InviteCoOwnerForm,
    MortgageForm,
    OwnerMonthlyPaymentForm,
    PropertyForm,
    PropertyTaxForm,
    RateChangeForm,
    RentalIncomeForm,
    ValuationForm,
)
from .models import (
    Mortgage,
    MortgageRateChange,
    OwnerMonthlyPayment,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyExpense,
    PropertyInvitation,
    PropertyNotification,
    PropertyOwnership,
    PropertyTax,
    PropertyValuation,
    RentalIncome,
)
from .services import (
    calculate_monthly_cost,
    estimate_sale_proceeds,
    generate_amortization_schedule,
    generate_evolution_chart_data,
    generate_per_owner_amortization,
    get_current_ownership_shares,
    get_owner_snapshot,
    get_ownership_comparison,
    get_property_snapshot,
    get_total_paid,
    notify_co_owners,
)
from .tooltips import get_tooltips

User = get_user_model()

TWO_PLACES = Decimal("0.01")
OTHER_CURRENCY = {"CAD": "EUR", "EUR": "CAD"}


@login_required
def property_list(request):
    properties = Property.objects.filter(owners=request.user)
    summaries = []
    for prop in properties:
        snapshot = get_owner_snapshot(prop, request.user)
        cost = calculate_monthly_cost(prop, for_user=request.user)
        summaries.append({"property": prop, "snapshot": snapshot, "monthly_cost": cost})
    return render(request, "real_estate/list.html", {"summaries": summaries, "tips": get_tooltips()})


@login_required
def property_create(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        country = request.POST.get("country", "CA")
        mortgage_form = MortgageForm(request.POST, prefix="mortgage", country=country)
        if form.is_valid() and mortgage_form.is_valid():
            prop = form.save()
            down_payment = form.cleaned_data.get("down_payment") or Decimal("0")
            ownership = PropertyOwnership.objects.create(
                user=request.user, property=prop, is_admin=True, down_payment=down_payment
            )

            co_email = form.cleaned_data.get("co_owner_email")
            co_share = form.cleaned_data.get("co_owner_share") or Decimal("50")
            creator_share = Decimal("100") - co_share if co_email else Decimal("100")

            period = OwnershipPeriod.objects.create(property=prop, start_date=prop.purchase_date)
            OwnershipPeriodShare.objects.create(period=period, owner=ownership, share_pct=creator_share)

            if co_email:
                co_down = form.cleaned_data.get("co_owner_down_payment") or Decimal("0")
                invitation = PropertyInvitation.objects.create(
                    property=prop,
                    invited_by=request.user,
                    email=co_email,
                    down_payment=co_down,
                    share_pct=co_share,
                    token=get_random_string(64),
                )
                _notify_invitee(invitation)

            if mortgage_form.cleaned_data.get("principal"):
                mortgage = mortgage_form.save(commit=False)
                mortgage.real_estate = prop
                mortgage.save()
            return redirect("real_estate:detail", pk=prop.pk)
    else:
        form = PropertyForm()
        mortgage_form = MortgageForm(prefix="mortgage")
    return render(request, "real_estate/create.html", {"form": form, "mortgage_form": mortgage_form})


@login_required
def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    ownership = prop.ownerships.get(user=request.user)
    snapshot = get_property_snapshot(prop)
    owner_snapshot = get_owner_snapshot(prop, request.user)
    shares = get_current_ownership_shares(prop)
    sale_estimate = estimate_sale_proceeds(prop)
    active_mortgage = prop.mortgages.filter(is_active=True).first()
    expenses = prop.expenses.all()[:20]
    valuations = prop.valuations.all()[:10]
    taxes = prop.taxes.all()
    pending_invitations = prop.invitations.filter(accepted=False)

    # Chart data
    equity_chart = json.dumps(
        {
            "labels": [str(_("Equity")), str(_("Remaining mortgage"))],
            "values": [float(snapshot["equity"]), float(snapshot["mortgage_balance"])],
            "colors": ["#10b981", "#e2e8f0"],
        }
    )

    total_principal_paid = Decimal("0")
    total_interest_paid = Decimal("0")
    remaining_principal = Decimal("0")
    if active_mortgage:
        paid_data = get_total_paid(active_mortgage)
        total_principal_paid = paid_data["total_principal_paid"]
        total_interest_paid = paid_data["total_interest_paid"]
        remaining_principal = snapshot["mortgage_balance"]

    payment_chart = json.dumps(
        {
            "labels": [
                str(_("Principal paid")),
                str(_("Interest paid")),
                str(_("Remaining principal")),
            ],
            "values": [
                float(total_principal_paid),
                float(total_interest_paid),
                float(remaining_principal),
            ],
            "colors": ["#10b981", "#f59e0b", "#e2e8f0"],
        }
    )

    expense_by_type = {}
    for exp in prop.expenses.all():
        label = exp.get_expense_type_display()
        expense_by_type[label] = expense_by_type.get(label, 0) + float(exp.amount)
    expense_chart = json.dumps(
        {
            "labels": list(expense_by_type.keys()) or [str(_("No expenses"))],
            "values": list(expense_by_type.values()) or [0],
        }
    )

    monthly_cost = calculate_monthly_cost(prop, for_user=request.user)
    evolution_chart = None
    if active_mortgage:
        evolution_chart = json.dumps(generate_evolution_chart_data(active_mortgage))
    rental_incomes = prop.rental_incomes.all()
    owner_payment_form = OwnerMonthlyPaymentForm(prop=prop) if active_mortgage else None

    has_co_owners = shares and len(shares) > 1
    cost_total = calculate_monthly_cost(prop)
    cost_mine = calculate_monthly_cost(prop, for_user=request.user)
    ownership_comparison = get_ownership_comparison(prop)

    # Mortgage as % of property value
    mortgage_pct = ""
    if snapshot["mortgage_balance"] and prop.current_valuation:
        pct_val = (snapshot["mortgage_balance"] / prop.current_valuation * 100).quantize(Decimal("0.1"))
        mortgage_pct = _("%(pct)s%% of value") % {"pct": pct_val}

    return render(
        request,
        "real_estate/detail.html",
        {
            "property": prop,
            "ownership": ownership,
            "snapshot": snapshot,
            "owner_snapshot": owner_snapshot,
            "shares": shares,
            "sale_estimate": sale_estimate,
            "mortgage": active_mortgage,
            "expenses": expenses,
            "valuations": valuations,
            "taxes": taxes,
            "pending_invitations": pending_invitations,
            "equity_chart": equity_chart,
            "payment_chart": payment_chart,
            "expense_chart": expense_chart,
            "evolution_chart": evolution_chart,
            "monthly_cost": monthly_cost,
            "cost_total": cost_total,
            "cost_mine": cost_mine,
            "has_co_owners": has_co_owners,
            "rental_incomes": rental_incomes,
            "owner_payment_form": owner_payment_form,
            "ownership_comparison": ownership_comparison,
            "mortgage_pct": mortgage_pct,
            "tips": get_tooltips(prop.country),
        },
    )


@login_required
def property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    ownership = get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    active_mortgage = prop.mortgages.filter(is_active=True).first()
    pending_invitations = prop.invitations.filter(accepted=False)
    if request.method == "POST":
        form = PropertyForm(request.POST, instance=prop)
        mortgage_form = (
            MortgageForm(request.POST, prefix="mortgage", instance=active_mortgage, country=prop.country)
            if active_mortgage
            else None
        )
        if form.is_valid() and (mortgage_form is None or mortgage_form.is_valid()):
            form.save()
            if mortgage_form:
                mortgage_form.save()
            notify_co_owners(prop, request.user, "property_updated", _("updated property details"))
            return redirect("real_estate:detail", pk=prop.pk)
    else:
        form = PropertyForm(instance=prop)
        mortgage_form = (
            MortgageForm(prefix="mortgage", instance=active_mortgage, country=prop.country) if active_mortgage else None
        )
    return render(
        request,
        "real_estate/edit.html",
        {
            "form": form,
            "mortgage_form": mortgage_form,
            "property": prop,
            "ownership": ownership,
            "pending_invitations": pending_invitations,
        },
    )


@login_required
def add_expense(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    ownership = prop.ownerships.get(user=request.user)
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.property = prop
            expense.paid_by = ownership
            expense.save()
            notify_co_owners(
                prop,
                request.user,
                "expense_added",
                _('added expense "%(desc)s" (%(amount)s)') % {"desc": expense.description, "amount": expense.amount},
            )
            expenses = prop.expenses.all()[:20]
            response = render(
                request, "real_estate/partials/expense_list.html", {"expenses": expenses, "property": prop}
            )
            response["HX-Trigger"] = "expenses-changed"
            return response
    form = ExpenseForm()
    return render(request, "real_estate/partials/expense_form.html", {"form": form, "property": prop})


@login_required
def add_valuation(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    if request.method == "POST":
        form = ValuationForm(request.POST)
        if form.is_valid():
            valuation = form.save(commit=False)
            valuation.property = prop
            valuation.save()
            prop.current_valuation = valuation.value
            prop.valuation_date = valuation.date
            prop.save(update_fields=["current_valuation", "valuation_date"])
            notify_co_owners(
                prop,
                request.user,
                "valuation_added",
                _("added valuation of %(value)s") % {"value": valuation.value},
            )
            response = HttpResponse()
            response["HX-Redirect"] = reverse("real_estate:detail", args=[prop.pk])
            return response
    form = ValuationForm()
    return render(request, "real_estate/partials/valuation_form.html", {"form": form, "property": prop})


@login_required
def amortization_view(request, pk, mortgage_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    today = date.today()
    paid = get_total_paid(mortgage)

    shares = get_current_ownership_shares(prop)
    has_co_owners = len(shares) > 1

    owner_summaries = []
    owner_paid_to_date = {}
    owners_list = []
    ownership_evolution = []

    if has_co_owners:
        schedule, owner_summaries = generate_per_owner_amortization(mortgage)
        owners_list = [s["owner"] for s in owner_summaries]

        # Per-owner paid to date
        for o in owners_list:
            owner_paid_to_date[o.pk] = {"principal": Decimal("0"), "interest": Decimal("0"), "total": Decimal("0")}
        for entry in schedule:
            if entry["date"] > today:
                break
            for o in owners_list:
                op = entry.get("owner_payments", {}).get(o.pk)
                if op:
                    owner_paid_to_date[o.pk]["principal"] += op["principal"]
                    owner_paid_to_date[o.pk]["interest"] += op["interest"]
                    owner_paid_to_date[o.pk]["total"] += op["payment"]

        # Ownership evolution: yearly snapshots of cumulative contribution %
        yearly_totals = {}
        running = {o.pk: Decimal("0") for o in owners_list}
        for entry in schedule:
            for o in owners_list:
                op = entry.get("owner_payments", {}).get(o.pk)
                if op:
                    running[o.pk] += op["payment"]
            year = entry["date"].year
            if year not in yearly_totals:
                yearly_totals[year] = {}
            yearly_totals[year] = dict(running)

        for year in sorted(yearly_totals.keys()):
            totals = yearly_totals[year]
            grand = sum(totals.values())
            row = {"year": year, "owners": {}}
            for o in owners_list:
                pct = (totals[o.pk] / grand * 100).quantize(TWO_PLACES) if grand else Decimal("0")
                row["owners"][o.pk] = pct
            ownership_evolution.append(row)
    else:
        schedule = generate_amortization_schedule(mortgage)

    for entry in schedule:
        entry["is_current"] = entry["date"].year == today.year and entry["date"].month == today.month

    return render(
        request,
        "real_estate/amortization.html",
        {
            "property": prop,
            "mortgage": mortgage,
            "schedule": schedule,
            "paid": paid,
            "has_co_owners": has_co_owners,
            "owner_summaries": owner_summaries,
            "owner_paid_to_date": owner_paid_to_date,
            "owners_list": owners_list,
            "ownership_evolution": ownership_evolution,
            "tips": get_tooltips(prop.country),
        },
    )


@login_required
def add_tax(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    if request.method == "POST":
        form = PropertyTaxForm(request.POST, country=prop.country)
        if form.is_valid():
            tax = form.save(commit=False)
            tax.property = prop
            if PropertyTax.objects.filter(
                property=prop,
                tax_type=tax.tax_type,
                year=tax.year,
            ).exists():
                form.add_error(None, _("A tax entry for this type and year already exists."))
                return render(request, "real_estate/partials/tax_form.html", {"form": form, "property": prop})
            tax.save()
            notify_co_owners(
                prop,
                request.user,
                "tax_added",
                _("added %(type)s tax for %(year)s (%(amount)s)")
                % {"type": tax.get_tax_type_display(), "year": tax.year, "amount": tax.amount},
            )
            taxes = prop.taxes.all()
            response = render(request, "real_estate/partials/tax_list.html", {"taxes": taxes, "property": prop})
            response["HX-Trigger"] = "taxes-changed"
            return response
    else:
        form = PropertyTaxForm(country=prop.country)
    return render(request, "real_estate/partials/tax_form.html", {"form": form, "property": prop})


@login_required
def sale_simulator(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    sale_price_str = request.GET.get("sale_price")
    commission_str = request.GET.get("commission", "5")
    try:
        sale_price = Decimal(sale_price_str) if sale_price_str else None
    except (InvalidOperation, TypeError):
        sale_price = None
    try:
        commission = Decimal(commission_str)
    except (InvalidOperation, TypeError):
        commission = Decimal("5")
    estimate = estimate_sale_proceeds(prop, sale_price=sale_price, agent_commission_pct=commission)
    return render(
        request,
        "real_estate/partials/sale_estimate.html",
        {"property": prop, "estimate": estimate, "tips": get_tooltips(prop.country)},
    )


def _notify_invitee(invitation):
    """Create an invitation_received notification for the invitee if they have an account."""
    invitee = User.objects.filter(email=invitation.email).first()
    if not invitee:
        return
    PropertyNotification.objects.create(
        recipient=invitee,
        property=invitation.property,
        actor=invitation.invited_by,
        verb="invitation_received",
        description=_("invited you to co-own %(name)s (%(share)s%%)")
        % {
            "name": invitation.property.name,
            "share": invitation.share_pct,
        },
        invitation=invitation,
    )


@login_required
def invite_co_owner(request, property_id=None, pk=None):
    pk = pk or property_id
    prop = get_object_or_404(Property, pk=pk)
    get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    if request.method == "POST":
        form = InviteCoOwnerForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.property = prop
            invitation.invited_by = request.user
            invitation.token = get_random_string(64)
            invitation.save()
            notify_co_owners(
                prop,
                request.user,
                "invitation_sent",
                _("invited %(email)s as co-owner") % {"email": invitation.email},
            )
            _notify_invitee(invitation)
            messages.success(request, _("Invitation sent to %(email)s.") % {"email": invitation.email})
            return redirect("real_estate:detail", pk=prop.pk)
    else:
        form = InviteCoOwnerForm()
    return render(request, "real_estate/invite.html", {"property": prop, "form": form})


@login_required
def accept_invitation(request, token):
    invitation = get_object_or_404(PropertyInvitation, token=token, accepted=False)
    if request.user.email != invitation.email:
        messages.error(request, _("This invitation is for a different email address."))
        return redirect("home")
    prop = invitation.property
    ownership = PropertyOwnership.objects.create(
        user=request.user,
        property=prop,
        is_admin=False,
        down_payment=invitation.down_payment,
    )
    invitation.accepted = True
    invitation.save()

    # Update ownership period shares to reflect the split
    creator_share = Decimal("100") - invitation.share_pct
    current_period = prop.ownership_periods.filter(end_date__isnull=True).order_by("-start_date").first()
    if current_period:
        current_period.shares.all().delete()
        creator_ownership = prop.ownerships.get(is_admin=True)
        OwnershipPeriodShare.objects.create(period=current_period, owner=creator_ownership, share_pct=creator_share)
        OwnershipPeriodShare.objects.create(period=current_period, owner=ownership, share_pct=invitation.share_pct)

    notify_co_owners(
        prop,
        request.user,
        "invitation_accepted",
        _("accepted co-ownership invitation"),
    )
    messages.success(request, _("You are now a co-owner of %(name)s.") % {"name": prop.name})
    return redirect("real_estate:detail", pk=prop.pk)


@login_required
def accept_invitation_htmx(request, invitation_id):
    invitation = get_object_or_404(PropertyInvitation, pk=invitation_id, accepted=False)
    if request.user.email != invitation.email:
        return HttpResponseForbidden()
    prop = invitation.property
    ownership = PropertyOwnership.objects.create(
        user=request.user,
        property=prop,
        is_admin=False,
        down_payment=invitation.down_payment,
    )
    invitation.accepted = True
    invitation.save()

    creator_share = Decimal("100") - invitation.share_pct
    current_period = prop.ownership_periods.filter(end_date__isnull=True).order_by("-start_date").first()
    if current_period:
        current_period.shares.all().delete()
        creator_ownership = prop.ownerships.get(is_admin=True)
        OwnershipPeriodShare.objects.create(period=current_period, owner=creator_ownership, share_pct=creator_share)
        OwnershipPeriodShare.objects.create(period=current_period, owner=ownership, share_pct=invitation.share_pct)

    notify_co_owners(prop, request.user, "invitation_accepted", _("accepted co-ownership invitation"))

    # Mark related notifications as read
    PropertyNotification.objects.filter(recipient=request.user, invitation=invitation).update(is_read=True)

    return render(
        request,
        "real_estate/partials/invitation_response.html",
        {"accepted": True, "property": prop},
    )


@login_required
def decline_invitation_htmx(request, invitation_id):
    invitation = get_object_or_404(PropertyInvitation, pk=invitation_id, accepted=False)
    if request.user.email != invitation.email:
        return HttpResponseForbidden()

    # Mark related notifications as read
    PropertyNotification.objects.filter(recipient=request.user, invitation=invitation).update(is_read=True)

    invitation.delete()

    return render(
        request,
        "real_estate/partials/invitation_response.html",
        {"accepted": False},
    )


@login_required
def manage_ownership_periods(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    periods = prop.ownership_periods.prefetch_related("shares__owner__user").all()
    return render(request, "real_estate/ownership_periods.html", {"property": prop, "periods": periods})


@login_required
def notification_list(request):
    notifications = PropertyNotification.objects.filter(recipient=request.user).select_related(
        "property", "actor", "invitation"
    )[:50]
    return render(request, "real_estate/notifications.html", {"notifications": notifications})


@login_required
def mark_notifications_read(request):
    PropertyNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return render(request, "real_estate/partials/notification_badge.html")


@login_required
def edit_expense(request, pk, expense_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    expense = get_object_or_404(PropertyExpense, pk=expense_id, property=prop)
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            notify_co_owners(
                prop,
                request.user,
                "expense_updated",
                _('updated expense "%(desc)s" (%(amount)s)') % {"desc": expense.description, "amount": expense.amount},
            )
            expenses = prop.expenses.all()[:20]
            response = render(
                request, "real_estate/partials/expense_list.html", {"expenses": expenses, "property": prop}
            )
            response["HX-Trigger"] = "expenses-changed"
            return response
    else:
        form = ExpenseForm(instance=expense)
    return render(
        request,
        "real_estate/partials/expense_form.html",
        {"form": form, "property": prop, "editing": True, "expense": expense},
    )


@login_required
def delete_expense(request, pk, expense_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    expense = get_object_or_404(PropertyExpense, pk=expense_id, property=prop)
    if request.method == "DELETE":
        description = _('deleted expense "%(desc)s" (%(amount)s)') % {
            "desc": expense.description,
            "amount": expense.amount,
        }
        expense.delete()
        notify_co_owners(prop, request.user, "expense_deleted", description)
        expenses = prop.expenses.all()[:20]
        response = render(request, "real_estate/partials/expense_list.html", {"expenses": expenses, "property": prop})
        response["HX-Trigger"] = "expenses-changed"
        return response
    return HttpResponseNotAllowed(["DELETE"])


@login_required
def edit_tax(request, pk, tax_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    tax = get_object_or_404(PropertyTax, pk=tax_id, property=prop)
    if request.method == "POST":
        form = PropertyTaxForm(request.POST, instance=tax, country=prop.country)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.property = prop
            if (
                PropertyTax.objects.filter(property=prop, tax_type=updated.tax_type, year=updated.year)
                .exclude(pk=tax.pk)
                .exists()
            ):
                form.add_error(None, _("A tax entry for this type and year already exists."))
                return render(
                    request,
                    "real_estate/partials/tax_form.html",
                    {"form": form, "property": prop, "editing": True, "tax": tax},
                )
            updated.save()
            notify_co_owners(
                prop,
                request.user,
                "tax_updated",
                _("updated %(type)s tax for %(year)s") % {"type": tax.get_tax_type_display(), "year": tax.year},
            )
            taxes = prop.taxes.all()
            response = render(request, "real_estate/partials/tax_list.html", {"taxes": taxes, "property": prop})
            response["HX-Trigger"] = "taxes-changed"
            return response
    else:
        form = PropertyTaxForm(instance=tax, country=prop.country)
    return render(
        request,
        "real_estate/partials/tax_form.html",
        {"form": form, "property": prop, "editing": True, "tax": tax},
    )


@login_required
def delete_tax(request, pk, tax_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    tax = get_object_or_404(PropertyTax, pk=tax_id, property=prop)
    if request.method == "DELETE":
        description = _("deleted %(type)s tax for %(year)s (%(amount)s)") % {
            "type": tax.get_tax_type_display(),
            "year": tax.year,
            "amount": tax.amount,
        }
        tax.delete()
        notify_co_owners(prop, request.user, "tax_deleted", description)
        taxes = prop.taxes.all()
        response = render(request, "real_estate/partials/tax_list.html", {"taxes": taxes, "property": prop})
        response["HX-Trigger"] = "taxes-changed"
        return response
    return HttpResponseNotAllowed(["DELETE"])


@login_required
def edit_valuation(request, pk, valuation_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    valuation = get_object_or_404(PropertyValuation, pk=valuation_id, property=prop)
    if request.method == "POST":
        form = ValuationForm(request.POST, instance=valuation)
        if form.is_valid():
            valuation = form.save()
            latest = prop.valuations.first()
            if latest and latest.pk == valuation.pk:
                prop.current_valuation = valuation.value
                prop.valuation_date = valuation.date
                prop.save(update_fields=["current_valuation", "valuation_date"])
            notify_co_owners(
                prop,
                request.user,
                "valuation_updated",
                _("updated valuation to %(value)s on %(date)s") % {"value": valuation.value, "date": valuation.date},
            )
            response = HttpResponse()
            response["HX-Redirect"] = reverse("real_estate:detail", args=[prop.pk])
            return response
    else:
        form = ValuationForm(instance=valuation)
    return render(
        request,
        "real_estate/partials/valuation_form.html",
        {"form": form, "property": prop, "editing": True, "valuation": valuation},
    )


@login_required
def delete_valuation(request, pk, valuation_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    valuation = get_object_or_404(PropertyValuation, pk=valuation_id, property=prop)
    if request.method == "DELETE":
        description = _("deleted valuation of %(value)s on %(date)s") % {
            "value": valuation.value,
            "date": valuation.date,
        }
        valuation.delete()
        latest = prop.valuations.first()
        if latest:
            prop.current_valuation = latest.value
            prop.valuation_date = latest.date
        else:
            prop.current_valuation = prop.purchase_price
            prop.valuation_date = prop.purchase_date
        prop.save(update_fields=["current_valuation", "valuation_date"])
        notify_co_owners(prop, request.user, "valuation_deleted", description)
        response = HttpResponse()
        response["HX-Redirect"] = reverse("real_estate:detail", args=[prop.pk])
        return response
    return HttpResponseNotAllowed(["DELETE"])


@login_required
def remove_co_owner(request, pk, ownership_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    target_ownership = get_object_or_404(PropertyOwnership, pk=ownership_id, property=prop)

    if target_ownership.user == request.user:
        messages.error(request, _("You cannot remove yourself."))
        return redirect("real_estate:detail", pk=prop.pk)

    if request.method == "POST":
        removed_user = target_ownership.user
        removed_name = removed_user.get_full_name() or removed_user.email

        current_period = prop.ownership_periods.filter(end_date__isnull=True).order_by("-start_date").first()
        today = date.today()

        if current_period:
            current_period.end_date = today
            current_period.save(update_fields=["end_date"])

        new_period = OwnershipPeriod.objects.create(
            property=prop,
            start_date=today,
            note=_("%(name)s removed") % {"name": removed_name},
        )

        target_ownership.delete()

        remaining = prop.ownerships.all()
        if remaining.count() == 1:
            OwnershipPeriodShare.objects.create(period=new_period, owner=remaining.first(), share_pct=Decimal("100"))
        else:
            share = (Decimal("100") / remaining.count()).quantize(Decimal("0.01"))
            for own in remaining:
                OwnershipPeriodShare.objects.create(period=new_period, owner=own, share_pct=share)

        PropertyNotification.objects.create(
            recipient=removed_user,
            property=prop,
            actor=request.user,
            verb="co_owner_removed",
            description=_("removed you from %(name)s") % {"name": prop.name},
        )
        notify_co_owners(
            prop,
            request.user,
            "co_owner_removed",
            _("removed %(name)s from this property") % {"name": removed_name},
        )

        messages.success(
            request,
            _("%(name)s has been removed from %(property)s.") % {"name": removed_name, "property": prop.name},
        )
        return redirect("real_estate:detail", pk=prop.pk)

    return render(
        request,
        "real_estate/confirm_remove_owner.html",
        {"property": prop, "target_ownership": target_ownership},
    )


@login_required
def toggle_currency(request):
    current = request.session.get("display_currency")
    target = request.GET.get("target")
    if current and current == target:
        request.session["display_currency"] = None
    else:
        request.session["display_currency"] = target
    return redirect(request.META.get("HTTP_REFERER", "/real-estate/"))


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
        ctx = {"rate_changes": rate_changes, "property": prop, "mortgage": mortgage}
        response = render(request, "real_estate/partials/rate_change_list.html", ctx)
        response["HX-Trigger"] = "mortgage-changed"
        return response
    ctx = {"form": form, "property": prop, "mortgage": mortgage}
    return render(request, "real_estate/partials/rate_change_form.html", ctx)


@login_required
def delete_rate_change(request, pk, mortgage_id, rc_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    rc = get_object_or_404(MortgageRateChange, pk=rc_id, mortgage=mortgage)
    if request.method == "DELETE":
        rc.delete()
        rate_changes = mortgage.rate_changes.all()
        ctx = {"rate_changes": rate_changes, "property": prop, "mortgage": mortgage}
        response = render(request, "real_estate/partials/rate_change_list.html", ctx)
        response["HX-Trigger"] = "mortgage-changed"
        return response
    rate_changes = mortgage.rate_changes.all()
    ctx = {"rate_changes": rate_changes, "property": prop, "mortgage": mortgage}
    return render(request, "real_estate/partials/rate_change_list.html", ctx)


@login_required
def add_rental_income(request, pk):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    form = RentalIncomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ri = form.save(commit=False)
        ri.real_estate = prop
        ri.save()
        notify_co_owners(prop, request.user, "property_updated", _("Rental income updated"))
        incomes = prop.rental_incomes.all()
        response = render(
            request,
            "real_estate/partials/rental_income_list.html",
            {"rental_incomes": incomes, "property": prop},
        )
        response["HX-Trigger"] = "rental-changed"
        return response
    return render(request, "real_estate/partials/rental_income_form.html", {"form": form, "property": prop})


@login_required
def delete_rental_income(request, pk, income_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    income = get_object_or_404(RentalIncome, pk=income_id, real_estate=prop)
    if request.method == "DELETE":
        income.delete()
        incomes = prop.rental_incomes.all()
        response = render(
            request,
            "real_estate/partials/rental_income_list.html",
            {"rental_incomes": incomes, "property": prop},
        )
        response["HX-Trigger"] = "rental-changed"
        return response
    incomes = prop.rental_incomes.all()
    return render(
        request,
        "real_estate/partials/rental_income_list.html",
        {"rental_incomes": incomes, "property": prop},
    )


@login_required
def monthly_cost_partial(request, pk):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    shares = get_current_ownership_shares(prop)
    has_co_owners = len(shares) > 1
    cost_total = calculate_monthly_cost(prop)
    cost_mine = calculate_monthly_cost(prop, for_user=request.user)
    return render(
        request,
        "real_estate/partials/monthly_cost.html",
        {
            "cost_total": cost_total,
            "cost_mine": cost_mine,
            "has_co_owners": has_co_owners,
            "property": prop,
        },
    )


@login_required
def charts_partial(request, pk):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    snapshot = get_property_snapshot(prop)
    active_mortgage = prop.mortgages.filter(is_active=True).first()

    equity_chart = json.dumps(
        {
            "labels": [str(_("Equity")), str(_("Remaining mortgage"))],
            "values": [float(snapshot["equity"]), float(snapshot["mortgage_balance"])],
            "colors": ["#10b981", "#e2e8f0"],
        }
    )

    total_principal_paid = Decimal("0")
    total_interest_paid = Decimal("0")
    remaining_principal = Decimal("0")
    if active_mortgage:
        paid_data = get_total_paid(active_mortgage)
        total_principal_paid = paid_data["total_principal_paid"]
        total_interest_paid = paid_data["total_interest_paid"]
        remaining_principal = snapshot["mortgage_balance"]

    payment_chart = json.dumps(
        {
            "labels": [
                str(_("Principal paid")),
                str(_("Interest paid")),
                str(_("Remaining principal")),
            ],
            "values": [
                float(total_principal_paid),
                float(total_interest_paid),
                float(remaining_principal),
            ],
            "colors": ["#10b981", "#f59e0b", "#e2e8f0"],
        }
    )

    expense_by_type = {}
    for exp in prop.expenses.all():
        label = exp.get_expense_type_display()
        expense_by_type[label] = expense_by_type.get(label, 0) + float(exp.amount)
    expense_chart = json.dumps(
        {
            "labels": list(expense_by_type.keys()) or [str(_("No expenses"))],
            "values": list(expense_by_type.values()) or [0],
        }
    )

    return render(
        request,
        "real_estate/partials/charts_sidebar.html",
        {
            "property": prop,
            "equity_chart": equity_chart,
            "payment_chart": payment_chart,
            "expense_chart": expense_chart,
            "tips": get_tooltips(prop.country),
        },
    )


@login_required
def owner_payments(request, pk, mortgage_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    form = OwnerMonthlyPaymentForm(request.POST or None, prop=prop)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False)
        payment.mortgage = mortgage
        # Use update_or_create to handle re-submission for same owner+date
        payment, _created = OwnerMonthlyPayment.objects.update_or_create(
            mortgage=mortgage,
            owner=payment.owner,
            effective_date=payment.effective_date,
            defaults={
                "monthly_amount": payment.monthly_amount,
                "note": payment.note,
            },
        )

        # Auto-calc other owner's payment (2 owners only)
        all_ownerships = list(prop.ownerships.all())
        if len(all_ownerships) == 2:
            other = next(o for o in all_ownerships if o != payment.owner)
            other_amount = mortgage.monthly_payment - payment.monthly_amount
            OwnerMonthlyPayment.objects.update_or_create(
                mortgage=mortgage,
                owner=other,
                effective_date=payment.effective_date,
                defaults={
                    "monthly_amount": other_amount,
                    "note": _("Auto-calculated from co-owner's payment"),
                },
            )

        notify_co_owners(prop, request.user, "property_updated", _("Payment split updated"))
        payments = mortgage.owner_payments.select_related("owner__user").all()
        response = render(
            request,
            "real_estate/partials/owner_payments_form.html",
            {
                "form": OwnerMonthlyPaymentForm(prop=prop),
                "payments": payments,
                "property": prop,
                "mortgage": mortgage,
            },
        )
        response["HX-Trigger"] = "payments-changed"
        return response
    payments = mortgage.owner_payments.select_related("owner__user").all()
    return render(
        request,
        "real_estate/partials/owner_payments_form.html",
        {
            "form": OwnerMonthlyPaymentForm(prop=prop),
            "payments": payments,
            "property": prop,
            "mortgage": mortgage,
        },
    )


@login_required
def edit_owner_payment(request, pk, mortgage_id, payment_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    payment = get_object_or_404(OwnerMonthlyPayment, pk=payment_id, mortgage=mortgage)
    if request.method == "POST":
        form = OwnerMonthlyPaymentForm(request.POST, instance=payment, prop=prop)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.mortgage = mortgage
            updated, _created = OwnerMonthlyPayment.objects.update_or_create(
                mortgage=mortgage,
                owner=updated.owner,
                effective_date=updated.effective_date,
                defaults={
                    "monthly_amount": updated.monthly_amount,
                    "note": updated.note,
                },
            )

            # Auto-calc other owner's payment (2 owners only)
            all_ownerships = list(prop.ownerships.all())
            if len(all_ownerships) == 2:
                other = next(o for o in all_ownerships if o != updated.owner)
                other_amount = mortgage.monthly_payment - updated.monthly_amount
                OwnerMonthlyPayment.objects.update_or_create(
                    mortgage=mortgage,
                    owner=other,
                    effective_date=updated.effective_date,
                    defaults={
                        "monthly_amount": other_amount,
                        "note": _("Auto-calculated from co-owner's payment"),
                    },
                )

            notify_co_owners(prop, request.user, "property_updated", _("Payment split updated"))
            payments = mortgage.owner_payments.select_related("owner__user").all()
            response = render(
                request,
                "real_estate/partials/owner_payments_form.html",
                {
                    "form": OwnerMonthlyPaymentForm(prop=prop),
                    "payments": payments,
                    "property": prop,
                    "mortgage": mortgage,
                },
            )
            response["HX-Trigger"] = "payments-changed"
            return response
    else:
        form = OwnerMonthlyPaymentForm(instance=payment, prop=prop)
    return render(
        request,
        "real_estate/partials/owner_payments_form.html",
        {
            "form": form,
            "payments": mortgage.owner_payments.select_related("owner__user").all(),
            "property": prop,
            "mortgage": mortgage,
            "editing": True,
            "payment": payment,
        },
    )


@login_required
def delete_owner_payment(request, pk, mortgage_id, payment_id):
    prop = get_object_or_404(Property.objects.filter(owners=request.user), pk=pk)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    payment = get_object_or_404(OwnerMonthlyPayment, pk=payment_id, mortgage=mortgage)
    if request.method == "DELETE":
        payment.delete()
        notify_co_owners(prop, request.user, "property_updated", _("Payment split deleted"))
        payments = mortgage.owner_payments.select_related("owner__user").all()
        response = render(
            request,
            "real_estate/partials/owner_payments_form.html",
            {
                "form": OwnerMonthlyPaymentForm(prop=prop),
                "payments": payments,
                "property": prop,
                "mortgage": mortgage,
            },
        )
        response["HX-Trigger"] = "payments-changed"
        return response
    return HttpResponseNotAllowed(["DELETE"])
