"""
URL configuration for governanceplatform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path
from django.views.generic.base import TemplateView
from django.views.i18n import JavaScriptCatalog, set_language
from two_factor.urls import urlpatterns as tf_urls
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from two_factor.views import LoginView

from governanceplatform import views
from governanceplatform.admin import admin_site
from governanceplatform.settings import DEBUG, REGULATOR_CONTACT, SITE_NAME

handler404 = "governanceplatform.views.custom_404_view"
handler500 = "governanceplatform.views.custom_500_view"


urlpatterns = [
    # Root
    path("", views.index, name="index"),
    # Admin
    path("admin/", admin_site.urls),
    # API
    path('api/v1/governanceplatform/', include('governanceplatform.api.v1.urls')),
    # Accounts
    path("account/", include("django.contrib.auth.urls")),
    path("", include(tf_urls)),
    path(
        "account/login",
        LoginView.as_view(
            extra_context={"site_name": SITE_NAME, "regulator": REGULATOR_CONTACT},
            template_name="registration/login.html",
            redirect_field_name="next",
        ),
        name="login",
    ),
    path(
        "account/signup/",
        views.registration_view,
        name="registration",
    ),
    path("activate/<str:token>/", views.activate_account, name="activate"),
    path(
        "account/edit/",
        views.edit_account,
        name="edit_account",
    ),
    # Incident notification
    path("incidents/", include("incidents.urls"), name="incidents"),
    # Report Wizard
    path("reporting/", include("reporting.urls"), name="reporting"),
    # Security objectives
    path(
        "securityobjectives/",
        include("securityobjectives.urls"),
        name="securityobjectives",
    ),
    path(
        "dependencies/",
        include("dependencies.urls"),
        name="dependencies",
    ),
    # Logout
    path("logout", views.logout_view, name="logout"),
    # Terms of Service
    path("accept_terms/", views.accept_terms, name="accept_terms"),
    path("terms/", views.terms, name="terms"),
    # Accessibility
    path("accessibility/", views.accessibility, name="accessibility"),
    # Privacy Policy
    path("privacy/", views.privacy, name="privacy"),
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="home/robots.txt",
            content_type="text/plain; charset=utf8",
            extra_context={"site_name": SITE_NAME, "regulator": REGULATOR_CONTACT},
        ),
    ),
    path(
        "humans.txt",
        TemplateView.as_view(
            template_name="home/humans.txt", content_type="text/plain; charset=utf8"
        ),
    ),
    path(
        ".well-known/security.txt",
        TemplateView.as_view(
            template_name="home/security.txt", content_type="text/plain; charset=utf8"
        ),
    ),
    # Language Selector
    path("set-language/", set_language, name="set_language"),
    # contact
    path("contact/", views.contact, name="contact"),
    path("captcha/", include("captcha.urls")),  # Captcha URL
    # basic healthcheck
    path("healthz", include("health_check.urls")),
    # URL patterns to serve the translations in JavaScript
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    # api token management
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]


if DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
