from django.urls import path
from .views import run_code_view

urlpatterns = [
    path("", run_code_view, name="run_code"),
]