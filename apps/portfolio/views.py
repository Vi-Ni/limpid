from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.education.services import get_next_lesson

from .models import Portfolio
from .services import (
    get_allocation_breakdown,
    get_clarity_score,
    get_exposure_breakdown,
    get_holdings_table,
    get_portfolio_snapshot,
)


@login_required
def dashboard_view(request):
    """Main dashboard showing portfolio overview."""
    portfolio = Portfolio.objects.filter(user=request.user).first()
    if not portfolio:
        return redirect("accounts:onboarding")

    snapshot = get_portfolio_snapshot(portfolio)
    allocation = get_allocation_breakdown(portfolio)
    exposures = get_exposure_breakdown(portfolio)
    clarity = get_clarity_score(request.user, portfolio)
    next_lesson = get_next_lesson(request.user)

    return render(
        request,
        "pages/dashboard.html",
        {
            "portfolio": portfolio,
            "snapshot": snapshot,
            "allocation": allocation,
            "exposures": exposures,
            "clarity": clarity,
            "next_lesson": next_lesson,
        },
    )


@login_required
def portfolio_list(request):
    """List user portfolios, redirect to detail if only one."""
    portfolios = Portfolio.objects.filter(user=request.user)
    if portfolios.count() == 1:
        return redirect("portfolio:detail", pk=portfolios.first().pk)
    return render(request, "portfolio/list.html", {"portfolios": portfolios})


@login_required
def portfolio_detail(request, pk):
    """Show portfolio detail with holdings and transactions."""
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    snapshot = get_portfolio_snapshot(portfolio)
    allocation = get_allocation_breakdown(portfolio)
    holdings = get_holdings_table(portfolio)
    transactions = portfolio.transactions.select_related("asset").all()[:20]

    return render(
        request,
        "portfolio/detail.html",
        {
            "portfolio": portfolio,
            "snapshot": snapshot,
            "allocation": allocation,
            "holdings": holdings,
            "transactions": transactions,
        },
    )
