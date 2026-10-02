from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import Profile

from .choices import AssessmentType
from .models import Assessment, AssessmentEvaluation, AssessmentExcercise
from .serializers import AssessmentSerializer, EvaluateAssessmentSerializer


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

        assessment = get_object_or_404(Assessment, pk=data["assessment_id"])
        evaluation = AssessmentEvaluation.objects.create(
            assessment=assessment,
            user_id=request.user,
            answers=data["answers"],
        )

        # TODO 1: request the evaluation from the LLM, sending the assessment exercises
        #         and the learner's answers (data["is_initial"] tells whether this is the baseline).
        # TODO 2: parse the LLM response, create a SkillHistory with the updated skill scores,
        #         set evaluation.updated_skills and evaluation.error_types, then save.
        # TODO 3: update the user's current skill scores from the new SkillHistory.

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
        skills = profile.skills

        # TODO a: generate the assessment of self.assessment_type with the LLM using the user's current skills.
        # TODO b: save the generated assessment (e.g. with insert_assessment).
        # TODO c: return the saved assessment serialized with AssessmentSerializer.

        return Response({"detail": "Not implemented."}, status=status.HTTP_501_NOT_IMPLEMENTED)


class GenerateExerciseView(GenerateAssessmentView):
    assessment_type = AssessmentType.EXCERCISE


class GenerateRealLifeView(GenerateAssessmentView):
    assessment_type = AssessmentType.REAL_LIFE
