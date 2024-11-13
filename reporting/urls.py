from django.urls import path

from .views import report_generation, reporting, risk_analysis_submission

urlpatterns = [
    # Report generation
    path("", reporting, name="reporting"),
    path("generate", report_generation, name="report_generation"),
    # Import risk analysis
    path("import_risk_analysis", risk_analysis_submission, name="import_risk_analysis"),
]
