from django.urls import path

from regulator import views

urlpatterns = [
    path("", views.index),
]
