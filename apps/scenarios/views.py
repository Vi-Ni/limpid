from django.shortcuts import render


def scenario_lab(request):
    """Scenario lab landing page."""
    return render(request, "scenarios/lab.html")
