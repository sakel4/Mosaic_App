from django.urls import path

from .views import InitialAssessmentsView


urlpatterns = [
    path("initial/", InitialAssessmentsView.as_view(), name="initial-assessments"),
]
