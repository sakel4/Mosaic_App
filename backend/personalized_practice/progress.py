from collections import defaultdict
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from user.permissions import IsLearnerRole
from .models import ProgressAttempt


def progress_for(user):
    attempts = list(ProgressAttempt.objects.filter(user=user).order_by("created_at", "id"))
    skills = defaultdict(list)
    daily = defaultdict(list)
    for attempt in attempts:
        skills[attempt.skill].append(attempt.correct)
        daily[timezone.localdate(attempt.created_at)].append(attempt.correct)
    today = timezone.localdate()
    day = today if today in daily else today - timedelta(days=1)
    streak = 0
    while day in daily:
        streak += 1
        day -= timedelta(days=1)
    skill_rows = []
    for index, (name, outcomes) in enumerate(sorted(skills.items()), 1):
        accuracy = round(sum(outcomes) / len(outcomes) * 100)
        previous = round(sum(outcomes[:-1]) / len(outcomes[:-1]) * 100) if len(outcomes) > 1 else accuracy
        skill_rows.append({"id": index, "name": name, "progress": accuracy, "change": accuracy - previous})
    achievements = []
    for threshold in (1, 10, 50, 100):
        if len(attempts) >= threshold:
            achievements.append({"id": threshold, "title": f"{threshold} activities completed", "description": "Every activity is another step forward.", "icon": "★"})
    history = []
    for offset in range(41, -1, -1):
        day = today - timedelta(days=offset)
        outcomes = daily.get(day, [])
        history.append({"date": day.isoformat(), "completed": len(outcomes), "accuracy": round(sum(outcomes) / len(outcomes) * 100) if outcomes else None})
    return {"exercisesCompleted": len(attempts), "currentStreak": streak, "skills": skill_rows, "achievements": achievements, "history": history}


class ProgressAttemptSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    exercise_id = serializers.CharField(max_length=100)
    skill = serializers.CharField(max_length=100)
    correct = serializers.BooleanField()
    response_time = serializers.IntegerField(min_value=0, max_value=2147483647, default=0)


class ProgressView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsLearnerRole)

    def get(self, request):
        return Response(progress_for(request.user))

    def post(self, request):
        serializer = ProgressAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        client_id = data.pop("client_id")
        ProgressAttempt.objects.get_or_create(user=request.user, client_id=client_id, defaults=data)
        return Response(progress_for(request.user))
