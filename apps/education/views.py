from django.shortcuts import render


def learning_path(request):
    """Learning path overview."""
    return render(request, "education/path.html")
