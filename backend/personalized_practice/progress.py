from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from assessments.models import RealLifeExerciseAttempt, SkillHistory
from user.models import Profile
from user.permissions import IsLearnerRole
from .models import ProgressAttempt, LearnerSkillBaseline

SKILL_FIELDS = (
    "phonological_awareness", "letter_sound_association", "decoding", "word_recognition",
    "naming_speed", "reading_fluency", "spelling", "comprehension", "working_memory",
)


def skill_label(name):
    return name.replace("*", "").replace("_", " ").strip().capitalize()


def progress_for(user):
    zone = ZoneInfo(settings.REAL_LIFE_TIME_ZONE)
    attempts = list(ProgressAttempt.objects.filter(user=user).order_by("created_at", "id"))
    real_life = list(RealLifeExerciseAttempt.objects.filter(user=user, completed_at__isnull=False))
    skills = defaultdict(list)
    daily = defaultdict(list)
    hourly = defaultdict(list)
    events = [(attempt.created_at, attempt.skill, attempt.correct) for attempt in attempts]
    events += [(attempt.completed_at, "Everyday reading", attempt.correct) for attempt in real_life]
    events.sort(key=lambda event: event[0])
    for created_at, skill, correct in events:
        skills[skill_label(skill)].append(correct)
        local = timezone.localtime(created_at, zone)
        daily[local.date()].append(correct)
        hourly[(local.date(), local.hour)].append(correct)
    today = timezone.localtime(timezone.now(), zone).date()
    day = today if today in daily else today - timedelta(days=1)
    streak = 0
    while day in daily:
        streak += 1
        day -= timedelta(days=1)

    # Accuracy uses only scored responses. Unscored completions still earn stars.
    skill_rows = {}
    for name, outcomes in sorted(skills.items()):
        scored = [outcome for outcome in outcomes if outcome is not None]
        if not scored:
            continue
        accuracy = round(sum(scored) / len(scored) * 100)
        previous = round(sum(scored[:-1]) / len(scored[:-1]) * 100) if len(scored) > 1 else accuracy
        skill_rows[name] = {"name": name, "progress": accuracy, "change": accuracy - previous, "metric": "accuracy"}

    # Server evaluation scores are distinct from percent-correct practice accuracy.
    for baseline in LearnerSkillBaseline.objects.filter(user=user, baseline_score__isnull=False):
        name = skill_label(baseline.skill)
        skill_rows[name] = {"name": name, "progress": round(baseline.baseline_score), "change": 0, "metric": "score"}
    profile = Profile.objects.select_related("skills").filter(user=user).first()
    histories = list(SkillHistory.objects.filter(assessment_evaluation__user_id=user).order_by("-created_at")[:2])
    if profile and profile.skills:
        for field in SKILL_FIELDS:
            value = getattr(profile.skills, field)
            if value is None:
                continue
            score = round(float(value))
            previous = getattr(histories[1], field) if len(histories) > 1 else None
            change = score - round(float(previous)) if previous is not None else 0
            name = skill_label(field)
            skill_rows[name] = {"name": name, "progress": score, "change": change, "metric": "score"}
    rows = [{"id": index, **row} for index, row in enumerate(sorted(skill_rows.values(), key=lambda row: row["name"]), 1)]
    achievements = []
    for threshold in (1, 10, 50, 100):
        if len(events) >= threshold:
            achievements.append({"id": threshold, "title": f"{threshold} activities completed", "description": "Every activity is another step forward.", "icon": "\u2605"})
    history = []
    for offset in range(41, -1, -1):
        day = today - timedelta(days=offset)
        outcomes = daily.get(day, [])
        scored = [outcome for outcome in outcomes if outcome is not None]
        history.append({"date": day.isoformat(), "completed": len(outcomes),
                        "accuracy": round(sum(scored) / len(scored) * 100) if scored else None})
    hourly_history = []
    for (day, hour), outcomes in sorted(hourly.items()):
        if not today - timedelta(days=41) <= day <= today:
            continue
        scored = [outcome for outcome in outcomes if outcome is not None]
        hourly_history.append({"date": day.isoformat(), "hour": hour, "completed": len(outcomes),
                               "accuracy": round(sum(scored) / len(scored) * 100) if scored else None})
    return {"exercisesCompleted": len(events), "currentStreak": streak, "skills": rows,
            "achievements": achievements, "history": history, "hourlyHistory": hourly_history, "timeZone": settings.REAL_LIFE_TIME_ZONE}


class ProgressAttemptSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    exercise_id = serializers.CharField(max_length=100)
    skill = serializers.CharField(max_length=100)
    correct = serializers.BooleanField(allow_null=True)
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
