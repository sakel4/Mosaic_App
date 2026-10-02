from django.db.models import Prefetch
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import Profile

from .choices import AssessmentType
from .models import Assessment, AssessmentExcercise
from .serializers import AssessmentSerializer


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
