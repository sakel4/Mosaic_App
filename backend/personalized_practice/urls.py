from django.urls import path

from personalized_practice.views import NextExerciseView


urlpatterns = [
    path("next/", NextExerciseView.as_view(), name="next-practice-exercise"),
]
