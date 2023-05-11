from django.shortcuts import render
from django_otp.decorators import otp_required

from governanceplatform.settings import SITE_NAME


@otp_required()
def index(request):
    return render(request, "operateur/index.html")


def terms(request):
    return render(request, "home/terms.html", context={"site_name": SITE_NAME})


def privacy(request):
    return render(request, "home/privacy_policy.html", context={"site_name": SITE_NAME})
