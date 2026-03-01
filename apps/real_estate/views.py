from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from .forms import ExpenseForm, InviteCoOwnerForm, MortgageForm, PropertyForm, ValuationForm
from .models import Mortgage, OwnershipPeriod, OwnershipPeriodShare, Property, PropertyInvitation, PropertyOwnership
from .services import (
    estimate_sale_proceeds,
    generate_amortization_schedule,
    get_current_ownership_shares,
    get_owner_snapshot,
    get_property_snapshot,
    get_total_paid,
)


@login_required
def property_list(request):
    properties = Property.objects.filter(owners=request.user)
    summaries = []
    for prop in properties:
        snapshot = get_owner_snapshot(prop, request.user)
        summaries.append({"property": prop, "snapshot": snapshot})
    return render(request, "real_estate/list.html", {"summaries": summaries})


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
        },
    )


@login_required
def property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    ownership = get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    if request.method == "POST":
        form = PropertyForm(request.POST, instance=prop)
        if form.is_valid():
            form.save()
            return redirect("real_estate:detail", pk=prop.pk)
    else:
        form = PropertyForm(instance=prop)
    return render(request, "real_estate/edit.html", {"form": form, "property": prop, "ownership": ownership})


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
            expenses = prop.expenses.all()[:20]
            return render(request, "real_estate/partials/expense_list.html", {"expenses": expenses})
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
            valuations = prop.valuations.all()[:10]
            return render(request, "real_estate/partials/valuation_history.html", {"valuations": valuations})
    form = ValuationForm()
    return render(request, "real_estate/partials/valuation_form.html", {"form": form, "property": prop})


@login_required
def amortization_view(request, pk, mortgage_id):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id, real_estate=prop)
    schedule = generate_amortization_schedule(mortgage)
    paid = get_total_paid(mortgage)
    return render(
        request,
        "real_estate/amortization.html",
        {
            "property": prop,
            "mortgage": mortgage,
            "schedule": schedule,
            "paid": paid,
        },
    )


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
    return render(request, "real_estate/partials/sale_estimate.html", {"property": prop, "estimate": estimate})


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

    messages.success(request, _("You are now a co-owner of %(name)s.") % {"name": prop.name})
    return redirect("real_estate:detail", pk=prop.pk)


@login_required
def manage_ownership_periods(request, pk):
    prop = get_object_or_404(Property, pk=pk, owners=request.user)
    get_object_or_404(PropertyOwnership, property=prop, user=request.user, is_admin=True)
    periods = prop.ownership_periods.prefetch_related("shares__owner__user").all()
    return render(request, "real_estate/ownership_periods.html", {"property": prop, "periods": periods})
