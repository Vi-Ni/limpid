from django.shortcuts import render


def directory(request):
    """Impact investment directory."""
    return render(request, "impact/directory.html")
