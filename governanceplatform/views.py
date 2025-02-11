import sys

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models.functions import Now
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from governanceplatform.models import Company
from incidents.decorators import check_user_is_correct

from .forms import (
    CustomUserChangeForm,
    RegistrationForm,
    SelectCompany,
    TermsAcceptanceForm,
)


@login_required
@check_user_is_correct
def index(request):
    user = request.user

    if not request.session.get("company_in_use") and user.companies.exists():
        if user.companies.distinct().count() > 1:
            return select_company(request)

        request.session["company_in_use"] = user.companies.first().id

    return redirect("incidents")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
@check_user_is_correct
def edit_account(request):
    user = request.user
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _("The account has been successfully saved."),
            )
    else:
        form = CustomUserChangeForm(instance=user)
    return render(request, "account/edit.html", {"form": form})


def about(request):
    python_version = "{}.{}.{}".format(*sys.version_info[:3])
    return render(request, "home/about.html", {"python_version": python_version})


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
            user = form.save()
            user.accepted_terms = True
            user.accepted_terms_date = Now()
            user.save()
            # default give the role IncidentUser
            new_group, created = Group.objects.get_or_create(name="IncidentUser")
            if new_group:
                user.groups.add(new_group)
            else:
                user.groups.add(created)
            email = form.cleaned_data.get("email").lower()
            raw_password = form.cleaned_data.get("password1")
            account = authenticate(email=email, password=raw_password)
            login(request, account)
            return redirect("index")
        else:
            context["form"] = form

    else:
        form = RegistrationForm()
        context["form"] = form
    return render(request, "registration/signup.html", context)


def select_company(request):
    if request.method == "POST":
        form = SelectCompany(request.POST, companies=request.user.companies.distinct())

        if form.is_valid() and request.user.is_authenticated:
            user_company = Company.objects.get(
                id=form.cleaned_data["select_company"].id
            )
            if user_company:
                request.session["company_in_use"] = user_company.id
                return index(request)

            messages.warning(
                request, "The select company is not linked to the account."
            )
    else:
        form = SelectCompany(companies=request.user.companies.distinct())

    return render(request, "registration/select_company.html", {"form": form})


@login_required
@check_user_is_correct
def accept_terms(request):
    if request.method == "POST":
        form = TermsAcceptanceForm(request.POST)
        if form.is_valid():
            request.user.accepted_terms = True
            request.user.accepted_terms_date = Now()
            request.user.save()
            return redirect("index")  # Redirect after accepting terms
    else:
        form = TermsAcceptanceForm()

    return render(request, "modals/accept_terms.html", {"form": form})


def contact(request):
    return render(request, "home/contact.html")


def custom_404_view(request, exception):
    return render(request, "404.html", status=404)
