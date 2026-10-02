from django.urls import path

from .views import EvaluateRealLifeSetView, RealLifeSetView


urlpatterns = [
    path("", RealLifeSetView.as_view(), name="real-life-set"),
    path("evaluate/", EvaluateRealLifeSetView.as_view(), name="evaluate-real-life-set"),
]
