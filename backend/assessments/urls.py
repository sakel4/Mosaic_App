from django.urls import path

from .views import EvaluateAssessmentView, GenerateExerciseView, GenerateRealLifeView, InitialAssessmentsView


urlpatterns = [
    path("initial/", InitialAssessmentsView.as_view(), name="initial-assessments"),
    path("evaluate/", EvaluateAssessmentView.as_view(), name="evaluate-assessment"),
    path("exercise/", GenerateExerciseView.as_view(), name="generate-exercise"),
    path("real_life/", GenerateRealLifeView.as_view(), name="generate-real-life"),
]
