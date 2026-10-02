from django.urls import path

from .views import EvaluateAssessmentView, GenerateExerciseView, GenerateRealLifeView, InitialAssessmentsView
from .real_life import DailyRealLifeExercisesView, CompleteRealLifeExerciseView


urlpatterns = [
    path("real_life/daily/", DailyRealLifeExercisesView.as_view(), name="daily-real-life"),
    path("real_life/<uuid:attempt_id>/complete/", CompleteRealLifeExerciseView.as_view(), name="complete-real-life"),
    path("initial/", InitialAssessmentsView.as_view(), name="initial-assessments"),
    path("evaluate/", EvaluateAssessmentView.as_view(), name="evaluate-assessment"),
    path("exercise/", GenerateExerciseView.as_view(), name="generate-exercise"),
    path("real_life/", GenerateRealLifeView.as_view(), name="generate-real-life"),
]
