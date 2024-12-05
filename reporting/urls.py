from django.urls import path

from .views import (
    add_report_configuration,
    edit_report_configuration,
    import_risk_analysis,
    report_configuration,
    report_generation,
    reporting,
)

urlpatterns = [
    # Report generation
    path("", reporting, name="reporting"),
    path("generate", report_generation, name="report_generation"),
    path("configuration", report_configuration, name="report_configuration"),
    path(
        "configuration/add", add_report_configuration, name="add_report_configuration"
    ),
    path(
        "configuration/edit/<int:report_configuration_id>",
        edit_report_configuration,
        name="edit_report_configuration",
    ),
    # Import risk analysis
    path("import_risk_analysis", import_risk_analysis, name="import_risk_analysis"),
]
