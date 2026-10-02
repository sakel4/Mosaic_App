import json
import logging
import os

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bedrock import BedrockError, BedrockNotConfigured
from user.models import Profile

from .choices import AssessmentType
from .evaluation import EvaluationError, evaluate_assessment
from .generation import AssessmentGenerationError, generate_assessment
from .models import Assessment, AssessmentExcercise
from .serializers import AssessmentSerializer, EvaluateAssessmentSerializer

logger = logging.getLogger(__name__)


class InitialAssessmentsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        profile = Profile.objects.filter(user_id=request.user.pk).only("age_group").first()
        if profile is None or not profile.age_group:
            return Response(
                {"detail": "Set the learner's age group before requesting assessments."},
                status=status.HTTP_409_CONFLICT,
            )

        assessments = (
            Assessment.objects.filter(
                assessment_type=AssessmentType.ASSESSMENT,
                age_group=profile.age_group,
            )
            .prefetch_related(
                Prefetch("excercises", queryset=AssessmentExcercise.objects.order_by("position"))
            )
            .order_by("-created_at")
        )
        return Response(AssessmentSerializer(assessments, many=True).data)


class EvaluateAssessmentView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = EvaluateAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        assessment = get_object_or_404(
            Assessment.objects.filter(Q(user__isnull=True) | Q(user=request.user)),
            pk=data["assessment_id"],
        )
        profile = Profile.objects.select_related("skills").filter(user_id=request.user.pk).first()
        if profile is None:
            return Response({"detail": "Learner profile not found."}, status=status.HTTP_409_CONFLICT)

        try:
            evaluation = evaluate_assessment(
                assessment=assessment,
                answers=data["answers"],
                user=request.user,
                profile=profile,
                is_initial=data["is_initial"],
            )
        except BedrockNotConfigured:
            return Response({"detail": "Evaluation is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (BedrockError, EvaluationError):
            logger.exception("Assessment evaluation failed")
            return Response({"detail": "Could not evaluate the assessment."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"id": evaluation.pk}, status=status.HTTP_201_CREATED)


class GenerateAssessmentView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    assessment_type = None

    def post(self, request):
        user = request.user
        if not (user.on_bording_completed and user.assessment_completed):
            return Response(
                {"detail": "Complete onboarding and the initial assessment before generating assessments."},
                status=status.HTTP_409_CONFLICT,
            )

        profile = Profile.objects.select_related("skills").filter(user_id=user.pk).first()
        if profile is None:
            return Response({"detail": "Learner profile not found."}, status=status.HTTP_409_CONFLICT)
        if not profile.age_group or profile.skills is None:
            return Response(
                {"detail": "The learner needs an age group and skill scores."},
                status=status.HTTP_409_CONFLICT,
            )
        skills = {
            field.name: getattr(profile.skills, field.name)
            for field in profile.skills._meta.concrete_fields
            if field.name != "id"
        }

        try:
            assessment = generate_assessment(
                assessment_type=self.assessment_type,
                age_group=profile.age_group,
                skills=skills,
                user=user,
            )
        except BedrockNotConfigured:
            return Response({"detail": "Generation is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (BedrockError, AssessmentGenerationError):
            logger.exception("Assessment generation failed")
            return Response({"detail": "Could not generate the assessment."}, status=status.HTTP_502_BAD_GATEWAY)

        data = AssessmentSerializer(assessment).data
        print(f"Bedrock model: {os.getenv('BEDROCK_MODEL_ID')}")
        print(json.dumps(data, indent=2, default=str))

        return Response(data, status=status.HTTP_201_CREATED)


class GenerateExerciseView(GenerateAssessmentView):
    assessment_type = AssessmentType.EXCERCISE


class GenerateRealLifeView(GenerateAssessmentView):
    assessment_type = AssessmentType.REAL_LIFE
