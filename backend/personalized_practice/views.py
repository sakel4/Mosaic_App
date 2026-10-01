from django.core.exceptions import ImproperlyConfigured
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from user.permissions import IsLearnerRole
from personalized_practice.domain import PracticeDataError
from personalized_practice.generator import BedrockExerciseGenerator, ExerciseGenerationError, ExerciseGenerationNotConfigured
from personalized_practice.orchestrator import PracticeOrchestrator
from personalized_practice.repository import get_repository
from personalized_practice.assessment import AssessmentSubmissionError, get_assessment_results, save_assessment_results
from personalized_practice.bank import load_age_bank
from personalized_practice.speech_scoring import (
    SpeechScoringError,
    SpeechServiceUnavailable,
    TranscribeSpeechScorer,
    verify_speech_result_token,
)
from user.models import Profile


class NextExerciseView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        try:
            repository = get_repository()
            orchestrator = PracticeOrchestrator(repository, BedrockExerciseGenerator())
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


class AssessmentResponseSerializer(serializers.Serializer):
    assessment_version = serializers.CharField()
    responses = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    speech_result_tokens = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict,
    )


class SubmitAssessmentView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def post(self, request):
        serializer = AssessmentResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = Profile.objects.filter(user_id=request.user.pk).only("age_group").first()
        if profile is None or not profile.age_group:
            return Response(
                {"detail": "Set the learner's age group before submitting the assessment."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            version = serializer.validated_data["assessment_version"]
            verified_speech_scores = {
                exercise_id: verify_speech_result_token(
                    token,
                    user_id=str(request.user.pk),
                    age_group=profile.age_group,
                    assessment_version=version,
                    exercise_id=exercise_id,
                )
                for exercise_id, token in serializer.validated_data["speech_result_tokens"].items()
            }
            results = get_assessment_results(
                profile.age_group,
                serializer.validated_data,
                verified_speech_scores,
            )
        except SpeechScoringError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AssessmentSubmissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        save_assessment_results(request.user, results)
        return Response(
            {
                "assessment_completed": True,
                "assessment_version": serializer.validated_data["assessment_version"],
                "skills": results,
            },
            status=status.HTTP_200_OK,
        )


class SpeechUploadSerializer(serializers.Serializer):
    assessment_version = serializers.CharField(max_length=80)
    exercise_id = serializers.CharField(max_length=100)
    audio = serializers.FileField()


class UploadSpeechAssessmentView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)
    parser_classes = (MultiPartParser, FormParser)
    throttle_scope = "speech_transcribe"

    def post(self, request):
        serializer = SpeechUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = Profile.objects.filter(user_id=request.user.pk).only("age_group").first()
        if profile is None or not profile.age_group:
            return Response(
                {"detail": "Set the learner's age group before uploading speech."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            result = TranscribeSpeechScorer().score_audio(
                str(request.user.pk),
                profile.age_group,
                serializer.validated_data["assessment_version"],
                serializer.validated_data["exercise_id"],
                serializer.validated_data["audio"],
            )
        except SpeechServiceUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except SpeechScoringError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)
