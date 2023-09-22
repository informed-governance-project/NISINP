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
from django.urls import path
from django.views.i18n import set_language

from .views import (
    download_incident_pdf,
    get_final_notification_list,
    get_form_list,
    get_incidents,
    get_incidents_for_regulator,
    get_regulator_incident_edit_form,
)

urlpatterns = [
    # Root
    path("", get_incidents, name="incidents"),
    path("set-language/", set_language, name="set_language"),
    # incident declaration
    path("declaration", get_form_list, name="declaration"),
    # incident declaration
    path(
        r"final-notification/<int:incident_id>",
        get_final_notification_list,
        name="final-notification",
    ),
    # incident list for regulator
    path("regulator/incidents", get_incidents_for_regulator, name="regulator_incidents"),
    path("regulator/incident/<int:incident_id>", get_regulator_incident_edit_form,
         name="regulator_incident_edit"),
    path("regulator/download-pdf/<int:incident_id>", download_incident_pdf,
         name="download_incident_pdf"),
]
