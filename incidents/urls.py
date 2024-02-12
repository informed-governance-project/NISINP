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
    create_workflow,
    download_incident_pdf,
    edit_impacts,
    edit_workflow,
    review_workflow,
    get_edit_incident_timeline_form,
    get_form_list,
    get_incidents,
    get_next_workflow,
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
        r"next_workflow/<int:incident_id>",
        get_next_workflow,
        name="next_workflow",
    ),
    path("create_workflow", create_workflow, name="create_workflow"),
    path("edit_workflow", edit_workflow, name="edit_workflow"),
    path("review_workflow", review_workflow, name="review_workflow"),
    path(
        r"edit_impacts/<int:incident_id>",
        edit_impacts,
        name="edit_impacts",
    ),
    path(
        "incident/<int:incident_id>",
        get_regulator_incident_edit_form,
        name="regulator_incident_edit",
    ),
    path(
        "download-pdf/<int:incident_id>",
        download_incident_pdf,
        name="download_incident_pdf",
    ),
    path(
        r"incident_edit_date/<int:incident_id>",
        get_edit_incident_timeline_form,
        name="edit_incident_timeline",
    ),
]
