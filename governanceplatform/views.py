import uuid
from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.mail import EmailMessage
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models.functions import Now
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from governanceplatform.models import Company
from incidents.decorators import check_user_is_correct

from .context_processors import user_modules
from .forms import (
    ContactForm,
    CustomUserChangeForm,
    RegistrationForm,
    SelectCompany,
    TermsAcceptanceForm,
)
from .helpers import is_user_regulator, send_activation_email
from .models import User
from .permissions import set_operator_admin_permissions, set_operator_user_permissions


@login_required
@check_user_is_correct
def index(request):
    return render(request, "home/index.html")


@login_required
@check_user_is_correct
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


def terms(request):
    return render(request, "home/terms.html")


def accessibility(request):
    return render(request, "home/accessibility.html")


def privacy(request):
    return render(request, "home/privacy_policy.html")


def cookies(request):
    context = {"cb_settings": settings.COOKIEBANNER}
    return render(request, "home/cookies_policy.html", context)


def sitemap(request):
    user = request.user
    available_modules = user_modules(request)["user_modules"]
    modules = OrderedDict(
        {
            _("Home"): [
                {"name": _("Terms of service"), "url": reverse("terms")},
                {"name": _("Cookies policy"), "url": reverse("cookies")},
                {"name": _("Accessibility statement"), "url": reverse("accessibility")},
            ],
            _("Account"): [
                {"name": _("Login"), "url": reverse("login")},
                {"name": _("Create account"), "url": reverse("registration")},
            ],
        }
    )

    if user.is_authenticated:
        modules[_("Home")].append({"name": _("Contact"), "url": reverse("contact")})
        if user.is_staff:
            modules[_("Home")].append(
                {"name": _("Settings"), "url": reverse("admin:index")}
            )

        modules[_("Account")] = [
            {"name": _("Account management"), "url": reverse("edit_account")},
            {"name": _("Account security"), "url": reverse("two_factor:profile")},
            {"name": _("Change password"), "url": reverse("password_change")},
            {"name": _("Log out"), "url": reverse("logout")},
        ]

        for a_module in available_modules:
            type_module = a_module["type"]
            if type_module == "incidents":
                incidents_pages = [
                    {"name": _("Overview"), "url": reverse("incidents")},
                    {"name": _("Report an incident"), "url": reverse("declaration")},
                ]
                if is_user_regulator(user):
                    incidents_pages.append(
                        {
                            "name": _("My reported incidents"),
                            "url": reverse("regulator_incidents"),
                        }
                    )
                modules[_("Incident notification")] = incidents_pages

            if type_module == "securityobjectives":
                securityobjectives_pages = [
                    {"name": _("Dashboard"), "url": reverse("securityobjectives")},
                ]

                modules[_("Security objectives")] = securityobjectives_pages

            if type_module == "reporting" and is_user_regulator(user):
                reporting_pages = [
                    {"name": _("Dashboard"), "url": reverse("reporting")},
                    {"name": _("Download Center"), "url": reverse("download_center")},
                    {
                        "name": _("Configuration"),
                        "url": reverse("report_configuration"),
                    },
                ]

                modules[_("Reporting")] = reporting_pages

    context = {"modules": modules}
    return render(request, "home/sitemap.html", context)


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
            user.is_active = False
            user.activation_token = uuid.uuid4()
            user.save()
            # default give the role IncidentUser
            new_group, created = Group.objects.get_or_create(name="IncidentUser")
            if new_group:
                user.groups.add(new_group)
            else:
                user.groups.add(created)
            send_activation_email(user)
            messages.info(request, _("An activation email has been sent."))
            return redirect("login")
        else:
            context["form"] = form

    else:
        form = RegistrationForm()
        context["form"] = form
    return render(request, "registration/signup.html", context)


# when we click on the link in the activation email
def activate_account(request, token):
    signer = TimestampSigner()
    try:
        user_activation_token = signer.unsign(
            token, max_age=settings.ACCOUNT_ACTIVATION_LINK_TIMEOUT
        )  # we check the token
        user = get_object_or_404(User, activation_token=user_activation_token)

        if not user.is_active:
            user.is_active = True
            user.activation_token = uuid.uuid4()  # deactivate previous link
            user.save()
            messages.success(
                request, _("Your account has been activated. You may log in now.")
            )
        else:
            messages.info(request, _("Your account is already active."))
    except SignatureExpired:
        messages.error(request, _("The link is expired."))
    except BadSignature:
        messages.error(request, _("Error"))  # invalid or expired link

    return redirect("login")


def select_company(request):
    if request.method == "POST":
        form = SelectCompany(
            request.POST,
            companies=request.user.companies.filter(
                companyuser__approved=True
            ).distinct(),
        )

        if form.is_valid() and request.user.is_authenticated:
            if not form.cleaned_data["select_company"]:
                return render(
                    request, "registration/select_company.html", {"form": form}
                )
            user_company = Company.objects.get(
                id=form.cleaned_data["select_company"].id
            )
            if user_company:
                user = request.user
                request.session["company_in_use"] = user_company.id
                is_administrator = user.companyuser_set.filter(
                    company=user_company, is_company_administrator=True
                ).exists()
                if is_administrator:
                    set_operator_admin_permissions(user)
                else:
                    set_operator_user_permissions(user)

                return index(request)

            messages.warning(
                request, "The select company is not linked to the account."
            )
    else:
        form = form = SelectCompany(
            companies=request.user.companies.filter(
                companyuser__approved=True
            ).distinct(),
        )

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


@login_required
def contact(request):
    user = request.user
    context = {}
    context["regulator"] = settings.REGULATOR_CONTACT
    if request.method == "POST":
        form = ContactForm(request.POST, user=user)

        if form.is_valid() and request.user.is_authenticated:
            # send email
            message = form.cleaned_data["message"]
            firstname = form.cleaned_data["firstname"]
            lastname = form.cleaned_data["lastname"]
            phone = form.cleaned_data["phone"]
            email = form.cleaned_data["email"]
            full_message = (
                f"Nom : {firstname} {lastname}\n"
                f"Email : {email}\n"
                f"Téléphone : {phone or 'Non renseigné'}\n\n"
                f"Message :\n{message}"
            )
            requestor_email = form.cleaned_data["email"].strip()
            email = EmailMessage(
                subject=_("%(name)s Contact page") % {"name": settings.SITE_NAME},
                body=full_message,
                from_email=settings.EMAIL_CONTACT_FROM,
                to=[settings.EMAIL_FOR_CONTACT],
                reply_to=[requestor_email],
                headers={"Return-Path": settings.EMAIL_CONTACT_FROM},
            )
            email.send()

            messages.success(request, _("Your message has been sent."))
            return redirect("contact")
        else:
            captcha_errors = form.errors.get("captcha")
            if captcha_errors:
                messages.error(request, _("Invalid captcha"))
            context["form"] = form
    else:
        form = ContactForm(user=user)
        context["form"] = form

    return render(request, "home/contact.html", context)


def custom_404_view(request, exception):
    return render(request, "parts/404.html", status=404)


def custom_500_view(request):
    return render(request, "parts/500.html", status=500)
