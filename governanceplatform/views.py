from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required

from .decorators import company_permission_required
from .forms import SelectCompany
from .models import Company


@login_required
def index(request):
    user = request.user

    if not user.is_verified():
        return redirect("two_factor:profile")

    otp_required(lambda req: index(req))

    if user.is_superuser:
        return redirect("admin:index")

    company_cookie = request.session.get("company_in_use")

    if user.companies.count() > 1 and not company_cookie:
        return select_company(request)

    if not company_cookie and user.companies.exists():
        company_cookie = user.companies.first().id

    try:
        user_company_selected = user.companies.get(id=company_cookie)
    except Company.DoesNotExist:
        messages.add_message(
            request,
            messages.ERROR,
            _(
                "There is no company associated with this account. Contact the administrator"
            ),
        )

        return redirect("login")

    if user.is_authenticated:
        if user_company_selected.is_regulator:
            return regulator_index(request)

        return operateur_index(request)

    return redirect("login")


def logout_view(request):
    logout(request)
    return redirect("login")


def terms(request):
    return render(request, "home/terms.html")


def privacy(request):
    return render(request, "home/privacy_policy.html")


@company_permission_required(is_regulator=False)
def operateur_index(request):
    return render(
        request,
        "operateur/index.html",
    )


@company_permission_required(is_regulator=True)
def regulator_index(request):
    return render(request, "regulator/index.html")


def select_company(request):
    if request.method == "POST":
        form = SelectCompany(request.POST, companies=request.user.companies)

        if form.is_valid() and request.user.is_authenticated:
            company_selected = form.cleaned_data["select_company"].id
            request.session["company_in_use"] = company_selected

            return index(request)
    else:
        form = SelectCompany(companies=request.user.companies)
    return render(request, "registration/select_company.html", {"form": form})
