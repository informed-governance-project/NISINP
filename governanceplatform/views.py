from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required

from .forms import CustomUserChangeForm, RegistrationForm, SelectCompany
from .helpers import user_in_group


@login_required
def index(request):
    user = request.user

    if not user.is_verified():
        return redirect("two_factor:profile")

    otp_required(lambda req: index(req))

    if user_in_group(user, "PlatformAdmin"):
        return redirect("admin:index")

    # TODO: allow to bypass it for an IncidentUser
    if not user.companies.exists():
        messages.error(
            request,
            _(
                "There is no company associated with this account. Contact the administrator"
            ),
        )
        return redirect("login")

    if not request.session.get("company_in_use"):
        if user.companies.count() > 1:
            return select_company(request)

        request.session["company_in_use"] = user.companies.first().id

    return (
        redirect("admin:index")
        if user_in_group(user, "RegulatorAdmin")
        else redirect("incidents")
    )


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def edit_account(request):
    user = request.user
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _("Account has been successfully saved."),
            )
    else:
        form = CustomUserChangeForm(instance=user)
    return render(request, "account/edit.html", {"form": form})


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


def select_company(request):
    if request.method == "POST":
        form = SelectCompany(request.POST, companies=request.user.companies)

        if form.is_valid() and request.user.is_authenticated:
            user_company = request.user.companies.get(
                id=form.cleaned_data["select_company"].id
            )
            if user_company:
                request.session["company_in_use"] = user_company.id
                return index(request)

            messages.warning(
                request, "The select company is not linked to the account."
            )
    else:
        form = SelectCompany(companies=request.user.companies)

    return render(request, "registration/select_company.html", {"form": form})
