from django.core.exceptions import ImproperlyConfigured
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from user.permissions import IsLearnerRole
from personalized_practice.domain import PracticeDataError
from personalized_practice.generator import (
    AnthropicExerciseGenerator,
    ExerciseGenerationError,
    ExerciseGenerationNotConfigured,
)
from personalized_practice.orchestrator import PracticeOrchestrator
from personalized_practice.repository import get_repository


class NextExerciseView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        try:
            repository = get_repository()
            orchestrator = PracticeOrchestrator(repository, AnthropicExerciseGenerator())
            result = orchestrator.next_exercise(str(request.user.pk))
        except ImproperlyConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ExerciseGenerationNotConfigured as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ExerciseGenerationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except PracticeDataError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(result, status=status.HTTP_201_CREATED)
