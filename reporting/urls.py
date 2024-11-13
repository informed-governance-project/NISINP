from django.urls import path

from reporting import views

from .views import risk_analysis_submission

urlpatterns = [
    # Report generation
    path("generate", views.report_generation, name="report_generation"),
    # Import risk analysis
    path("import_risk_analysis", risk_analysis_submission, name="import_risk_analysis"),
]
