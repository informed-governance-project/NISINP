from django.urls import path
from .views import full_sector_list_view

urlpatterns = [
    path("", full_sector_list_view, name="reporting"),
]
