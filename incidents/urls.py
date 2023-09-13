"""
URL configuration for nisinp project.

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

from incidents import views

from .views import (
    get_final_notification_list,
    get_form_list,
    get_incident_list,
    get_incident_list_for_regulator,
)

urlpatterns = [
    # Root
    path("", views.notifications, name="incidents"),
    path("set-language/", set_language, name="set_language"),
    # Notifications
    path("notifications/", views.notifications, name="notification"),
    # incident declaration
    path("notifications/declaration", get_form_list, name="declaration"),
    # incident list
    path("notifications/incident_list", get_incident_list, name="incident_list"),
    # incident declaration
    path(
        r"notifications/final-notification/<str:pk>",
        get_final_notification_list,
        name="final-notification",
    ),
    # incident list for regulator
    path(
        "regulator/incident_list", get_incident_list_for_regulator, name="incident_list"
    ),
    # API
    path("api-auth/", include("rest_framework.urls")),
    # path("api/v1/", include("incidents.api.urls")),
]
