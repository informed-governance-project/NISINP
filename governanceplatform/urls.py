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
from django.views.i18n import set_language
from two_factor.urls import urlpatterns as tf_urls
from two_factor.views import (
    BackupTokensView,
    LoginView,
    QRGeneratorView,
    SetupCompleteView,
    SetupView,
)

from governanceplatform import views
from governanceplatform.settings import DEBUG, REGULATOR_CONTACT, SITE_NAME

urlpatterns = [
    path("", include(tf_urls)),
    # Root
    path("", views.index, name="index"),
    # Regulator
    path("regulator/", include("regulator.urls")),
    # Operator
    path("operateur/", include("operateur.urls")),
    # Login
    path(
        "login",
        LoginView.as_view(
            extra_context={"site_name": SITE_NAME, "regulator": REGULATOR_CONTACT},
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path(
        "account/two_factor/setup/",
        SetupView.as_view(),
        name="setup",
    ),
    path(
        "account/two_factor/qrcode/",
        QRGeneratorView.as_view(),
        name="qr",
    ),
    path(
        "account/two_factor/setup/complete/",
        SetupCompleteView.as_view(),
        name="setup_complete",
    ),
    path(
        "account/two_factor/backup/tokens/",
        BackupTokensView.as_view(),
        name="backup_tokens",
    ),
    # Logout
    path("", include("django.contrib.auth.urls")),
    # Terms of Service
    path("terms/", views.terms, name="terms"),
    # Privacy Policy
    path("privacy/", views.privacy, name="privacy"),
    # Language Selector
    path("set-language/", set_language, name="set_language"),
]

if DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
