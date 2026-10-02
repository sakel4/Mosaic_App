import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bedrock import BedrockError, BedrockNotConfigured
from user.models import Profile

from .generation import RealLifeGenerationError, generate_real_life_set
from .serializers import RealLifeSetSerializer

logger = logging.getLogger(__name__)


class RealLifeSetView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        profile = Profile.objects.select_related("skills").filter(user_id=request.user.pk).first()
        if profile is None or not profile.age_group:
            return Response(
                {"detail": "Set the learner's age group before requesting a real-life set."},
                status=status.HTTP_409_CONFLICT,
            )

        skills = {}
        if profile.skills is not None:
            skills = {
                field.name: getattr(profile.skills, field.name)
                for field in profile.skills._meta.concrete_fields
                if field.name != "id"
            }

        try:
            real_life_set = generate_real_life_set(
                age_group=profile.age_group,
                interests=profile.interests,
                learning_goal=profile.learning_goal,
                skills=skills,
            )
        except BedrockNotConfigured:
            return Response({"detail": "Generation is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (BedrockError, RealLifeGenerationError):
            logger.exception("Real-life set generation failed")
            return Response({"detail": "Could not generate the real-life set."}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(RealLifeSetSerializer(real_life_set).data, status=status.HTTP_200_OK)
