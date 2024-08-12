from django.urls import path

from reporting import views

urlpatterns = [
    # Root
    path("", views.report_generation, name="report_generation"),
    # Admin
]
