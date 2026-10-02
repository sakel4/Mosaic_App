from django.urls import path

from .views import RealLifeSetView


urlpatterns = [
    path("", RealLifeSetView.as_view(), name="real-life-set"),
]
