from django.urls import path

from .views import EvaluateAssessmentView, InitialAssessmentsView


urlpatterns = [
    path("initial/", InitialAssessmentsView.as_view(), name="initial-assessments"),
    path("evaluate/", EvaluateAssessmentView.as_view(), name="evaluate-assessment"),
]
