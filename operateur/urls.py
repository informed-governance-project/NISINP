from django.urls import path

from operateur import views

urlpatterns = [
    path("", views.index),
]