from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def portfolio_list(request):
    """List user portfolios."""
    return render(request, "portfolio/list.html")
