from django.urls import path
from .views import run_code_view, submit_code_view

urlpatterns = [
    path("", run_code_view, name="run_code"),
    path("submit/", submit_code_view, name="submit"),
]