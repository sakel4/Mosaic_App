from django.urls import path

from .views import MeView
from .progress_email import ProgressEmailView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("progress/email/", ProgressEmailView.as_view(), name="progress-email"),
]
