from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url="login")
def index(request):
    return render(request, "operateur/index.html")


def terms(request):
    return render(request, "home/terms.html")


def privacy(request):
    return render(request, "home/privacy_policy.html")
