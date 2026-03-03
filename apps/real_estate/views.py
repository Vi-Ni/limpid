import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from .forms import ExpenseForm, InviteCoOwnerForm, MortgageForm, PropertyForm, PropertyTaxForm, ValuationForm
from .models import (
    Mortgage,
    OwnershipPeriod,
    OwnershipPeriodShare,
    Property,
    PropertyExpense,
    PropertyInvitation,
    PropertyNotification,
    PropertyOwnership,
    PropertyTax,
    PropertyValuation,
)
from .services import (
    estimate_sale_proceeds,
    generate_amortization_schedule,
    get_current_ownership_shares,
    get_owner_snapshot,
    get_property_snapshot,
    get_total_paid,
    notify_co_owners,
)
from .tooltips import TERM_TOOLTIPS

OTHER_CURRENCY = {"CAD": "EUR", "EUR": "CAD"}


@login_required
def property_list(request):
    properties = Property.objects.filter(owners=request.user)
    summaries = []
    for prop in properties:
        snapshot = get_owner_snapshot(prop, request.user)
        summaries.append({"property": prop, "snapshot": snapshot})
    return render(request, "real_estate/list.html", {"summaries": summaries, "tips": TERM_TOOLTIPS})


@login_required
def property_create(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        mortgage_form = MortgageForm(request.POST, prefix="mortgage")
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
                PropertyInvitation.objects.create(
                    property=prop,
                    invited_by=request.user,
                    email=co_email,
                    down_payment=co_down,
                    share_pct=co_share,
                    token=get_random_string(64),
                )

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
            "tips": TERM_TOOLTIPS,
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
            MortgageForm(request.POST, prefix="mortgage", instance=active_mortgage) if active_mortgage else None
        )
        if form.is_valid() and (mortgage_form is None or mortgage_form.is_valid()):
            form.save()
            if mortgage_form:
                mortgage_form.save()
            notify_co_owners(prop, request.user, "property_updated", _("updated property details"))
            return redirect("real_estate:detail", pk=prop.pk)
    else:
        form = PropertyForm(instance=prop)
        mortgage_form = MortgageForm(prefix="mortgage", instance=active_mortgage) if active_mortgage else None
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
            return render(request, "real_estate/partials/expense_list.html", {"expenses": expenses, "property": prop})
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
            valuations = prop.valuations.all()[:10]
            return render(
                request,
                "real_estate/partials/valuation_history.html",
                {"valuations": valuations, "oob_update": True, "property": prop},
            )
    form = ValuationForm()
    return render(request, "real_estate/partials/valuation_form.html", {"form": form, "property": prop})


@login_required
def amortization_view(request, pk, mortgage_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    schedule = generate_amortization_schedule(mortgage)
    today = date.today()
    for entry in schedule:
        entry["is_current"] = entry["date"].year == today.year and entry["date"].month == today.month
    paid = get_total_paid(mortgage)
    return render(
        request,
        "real_estate/amortization.html",
        {
            "property": prop,
            "mortgage": mortgage,
            "schedule": schedule,
            "paid": paid,
            "tips": TERM_TOOLTIPS,
        },
    )


@login_required
def add_tax(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    if request.method == "POST":
        form = PropertyTaxForm(request.POST)
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
            return render(request, "real_estate/partials/tax_list.html", {"taxes": taxes, "property": prop})
    else:
        form = PropertyTaxForm()
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
    return render(request, "real_estate/partials/sale_estimate.html", {"property": prop, "estimate": estimate, "tips": TERM_TOOLTIPS})


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
def manage_ownership_periods(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    periods = prop.ownership_periods.prefetch_related("shares__owner__user").all()
    return render(request, "real_estate/ownership_periods.html", {"property": prop, "periods": periods})


@login_required
def notification_list(request):
    notifications = PropertyNotification.objects.filter(recipient=request.user).select_related("property", "actor")[:50]
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
            return render(request, "real_estate/partials/expense_list.html", {"expenses": expenses, "property": prop})
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
        return render(request, "real_estate/partials/expense_list.html", {"expenses": expenses, "property": prop})
    return HttpResponseNotAllowed(["DELETE"])


@login_required
def edit_tax(request, pk, tax_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    tax = get_object_or_404(PropertyTax, pk=tax_id, property=prop)
    if request.method == "POST":
        form = PropertyTaxForm(request.POST, instance=tax)
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
            return render(request, "real_estate/partials/tax_list.html", {"taxes": taxes, "property": prop})
    else:
        form = PropertyTaxForm(instance=tax)
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
        return render(request, "real_estate/partials/tax_list.html", {"taxes": taxes, "property": prop})
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
            valuations = prop.valuations.all()[:10]
            return render(
                request,
                "real_estate/partials/valuation_history.html",
                {"valuations": valuations, "oob_update": True, "property": prop},
            )
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
        valuations = prop.valuations.all()[:10]
        return render(
            request,
            "real_estate/partials/valuation_history.html",
            {"valuations": valuations, "oob_update": True, "property": prop},
        )
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
