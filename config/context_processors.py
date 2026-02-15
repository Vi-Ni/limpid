def nav_current(request):
    """Determine the current navigation section from the URL path."""
    path = request.path
    if path.startswith("/portfolio"):
        section = "portfolios"
    elif path.startswith("/learn"):
        section = "learn"
    elif path.startswith("/scenarios"):
        section = "scenarios"
    elif path.startswith("/impact"):
        section = "impact"
    elif path.startswith("/accounts/profile") or path.startswith("/accounts/onboarding"):
        section = "profile"
    elif path == "/":
        section = "home"
    else:
        section = ""
    return {"nav_current": section}
