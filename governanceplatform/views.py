import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.mail import EmailMessage, send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models.functions import Now
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from governanceplatform.models import Company
from incidents.decorators import check_user_is_correct

from .forms import (
    ContactForm,
    CustomUserChangeForm,
    RegistrationForm,
    SelectCompany,
    TermsAcceptanceForm,
)
from .models import User
from .permissions import set_operator_admin_permissions, set_operator_user_permissions


@login_required
@check_user_is_correct
def index(request):
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


def terms(request):
    return render(request, "home/terms.html")


def accessibility(request):
    return render(request, "home/accessibility.html")


def privacy(request):
    return render(request, "home/privacy_policy.html")


# send an email with the token to activate the account
def send_activation_email(user):
    signer = TimestampSigner()
    token = signer.sign(user.activation_token)

    activation_link = (
        f"{settings.PUBLIC_URL}{reverse('activate', kwargs={'token': token})}"
    )

    subject = _("Activate your account")
    message = _(
        "Hello {username}! Please click here to activate your account : {activation_link}"
    ).format(username=user.first_name, activation_link=activation_link)

    send_mail(subject, message, settings.EMAIL_SENDER, [user.email])


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
        form = SelectCompany(request.POST, companies=request.user.companies.distinct())

        if form.is_valid() and request.user.is_authenticated:
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
    context = {}
    context["regulator"] = settings.REGULATOR_CONTACT
    if request.method == "POST":
        form = ContactForm(request.POST)

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
                subject=_("Contact page from %(name)s") % {"name": settings.SITE_NAME},
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
        form = ContactForm()
        context["form"] = form

    return render(request, "home/contact.html", context)


def custom_404_view(request, exception):
    return render(request, "parts/404.html", status=404)


def custom_500_view(request):
    return render(request, "parts/500.html", status=500)
