from django.urls import path

from reporting import views
from .views import risk_analysis_submission

urlpatterns = [
    # Root
    path("", views.report_generation, name="report_generation"),
    path("risk_analysis_submission", risk_analysis_submission, name="risk_analysis_submission"),
    # Admin
]
