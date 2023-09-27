from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required

from .forms import RegistrationForm, SelectCompany
from .helpers import user_in_group

User = get_user_model()


@login_required
def index(request):
    user = request.user

    if not user.is_verified():
        return redirect("two_factor:profile")

    otp_required(lambda req: index(req))

    if user_in_group(user, "PlatformAdmin") or user_in_group(user, "RegulatorAdmin"):
        return redirect("admin:index")

    if not user.companies.exists():
        messages.error(
            request,
            _(
                "There is no company associated with this account. Contact the administrator"
            ),
        )
        return redirect("login")

    company_cookie = request.session.get("company_in_use")
    if not company_cookie:
        if user.companies.count() > 1:
            return select_company(request)

        request.session["company_in_use"] = user.companies.first().id

    return redirect("incidents")


def logout_view(request):
    logout(request)
    return redirect("login")


def about(request):
    return render(request, "home/about.html")


def terms(request):
    return render(request, "home/terms.html")


def privacy(request):
    return render(request, "home/privacy_policy.html")


def registration_view(request, *args, **kwargs):
    context = {}
    user = request.user
    if user.is_authenticated:
        return redirect("index")
    elif request.method == "POST":
        print("hello")
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get("email").lower()
            raw_password = form.cleaned_data.get("password1")
            account = authenticate(email=email, password=raw_password)
            login(request, account)
            destination = kwargs.get("next")
            if destination:
                return redirect(destination)
            else:
                pass
        else:
            context["form"] = form

    else:
        form = RegistrationForm()
        context["form"] = form
    return render(request, "registration/signup.html", context)


# @company_permission_required(is_regulator=False)
# def operateur_index(request):
#     return render(
#         request,
#         "operateur/index.html",
#     )


# @company_permission_required(is_regulator=True)
# def regulator_index(request):
#     return render(request, "regulator/index.html")


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
