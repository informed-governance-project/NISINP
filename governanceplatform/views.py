from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from governanceplatform.settings import SITE_NAME


@login_required(login_url="login")
def index(request):
    return render(request, "operateur/index.html")


def terms(request):
    return render(request, "home/terms.html", context={"site_name": SITE_NAME})


def privacy(request):
    return render(request, "home/privacy_policy.html", context={"site_name": SITE_NAME})
