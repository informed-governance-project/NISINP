from django.urls import path

from .views import import_risk_analysis, report_generation, reporting

urlpatterns = [
    # Report generation
    path("", reporting, name="reporting"),
    path("generate", report_generation, name="report_generation"),
    # Import risk analysis
    path("import_risk_analysis", import_risk_analysis, name="import_risk_analysis"),
]
