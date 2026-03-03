def nav_current(request):
    """Determine the current navigation section from the URL path."""
    path = request.path
    if path.startswith("/real-estate/notifications"):
        section = "notifications"
    elif path.startswith("/dashboard"):
        section = "dashboard"
    elif path.startswith("/portfolio"):
        section = "portfolios"
    elif path.startswith("/learn"):
        section = "learn"
    elif path.startswith("/scenarios"):
        section = "scenarios"
    elif path.startswith("/impact"):
        section = "impact"
    elif path.startswith("/real-estate"):
        section = "real_estate"
    elif path.startswith("/accounts/profile") or path.startswith("/accounts/onboarding"):
        section = "profile"
    elif path == "/":
        section = "home"
    else:
        section = ""
    return {"nav_current": section}


def unread_notifications(request):
    if request.user.is_authenticated:
        from apps.real_estate.models import PropertyNotification

        count = PropertyNotification.objects.filter(recipient=request.user, is_read=False).count()
        return {"unread_notification_count": count}
    return {"unread_notification_count": 0}


def currency_context(request):
    display_currency = request.session.get("display_currency")
    return {"display_currency": display_currency}
