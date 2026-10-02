from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import Profile
from .models import RealLifeExercise, RealLifeExerciseAttempt


class RealLifeUnavailable(APIException):
    status_code = status.HTTP_409_CONFLICT


class RealLifeExerciseSerializer(serializers.ModelSerializer):
    information = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    options = serializers.ListField(child=serializers.CharField(), min_length=2)

    class Meta:
        model = RealLifeExercise
        fields = ["id", "age_group", "title", "context", "information", "question", "options", "correct_answer"]
        extra_kwargs = {"id": {"validators": []}}

    def validate(self, attrs):
        if attrs["correct_answer"] not in attrs["options"]:
            raise ValidationError("correct_answer must be one of the options.")
        if len(set(attrs["options"])) != len(attrs["options"]):
            raise ValidationError("Options must be distinct.")
        return attrs


def daily_window():
    zone = ZoneInfo(settings.REAL_LIFE_TIME_ZONE)
    today = timezone.localtime(timezone.now(), zone).date()
    tomorrow = datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone)
    return today, tomorrow


def attempt_payload(attempt):
    exercise = {key: value for key, value in attempt.exercise_data.items() if key not in ("correct_answer", "age_group")}
    return {
        "attempt_id": str(attempt.pk),
        "exercise": exercise,
        "completed_at": attempt.completed_at,
        "answer": attempt.answer if attempt.completed_at else None,
        "correct": attempt.correct if attempt.completed_at else None,
        "correct_answer": attempt.exercise_data["correct_answer"] if attempt.completed_at else None,
    }


class DailyRealLifeExercisesView(APIView):
    def get(self, request):
        # Serialize requests for this learner, including first assignment of the day.
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            today, tomorrow = daily_window()
            attempts = list(RealLifeExerciseAttempt.objects.filter(user=request.user, assigned_date=today))
            if not attempts:
                profile = Profile.objects.filter(user=request.user).first()
                if profile is None or not profile.age_group:
                    raise RealLifeUnavailable("Set the learner's age group first.")
                # Prefer exercises not assigned yesterday, then the least recently assigned.
                bank = list(RealLifeExercise.objects.filter(age_group=profile.age_group).order_by("id"))
                if len(bank) < 3:
                    raise RealLifeUnavailable("At least three real-life exercises are needed for this age group.")
                history = dict(RealLifeExerciseAttempt.objects.filter(user=request.user)
                               .values_list("exercise_id", "assigned_date").order_by("assigned_date"))
                bank.sort(key=lambda exercise: history.get(exercise.pk, today - timedelta(days=100000)))
                for slot, exercise in enumerate(bank[:3], start=1):
                    attempts.append(RealLifeExerciseAttempt.objects.create(
                        user=request.user, exercise=exercise, assigned_date=today, slot=slot,
                        exercise_data=dict(RealLifeExerciseSerializer(exercise).data),
                    ))
            completed = sum(attempt.completed_at is not None for attempt in attempts)
            return Response({
                "date": today, "daily_limit": 3, "completed": completed,
                "remaining": 3 - completed, "locked": completed == 3,
                "next_available_at": tomorrow, "exercises": [attempt_payload(attempt) for attempt in attempts],
            })


class CompleteRealLifeExerciseView(APIView):
    def post(self, request, attempt_id):
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            attempt = get_object_or_404(RealLifeExerciseAttempt, pk=attempt_id, user=request.user)
            # Retries return the original result and never consume another slot.
            if attempt.completed_at:
                return Response(attempt_payload(attempt))
            today, _ = daily_window()
            if attempt.assigned_date != today:
                raise RealLifeUnavailable("This exercise has expired. Get today's exercises.")
            answer = request.data.get("answer")
            if not isinstance(answer, str) or answer not in attempt.exercise_data["options"]:
                raise ValidationError({"answer": "Choose one of this exercise's options."})
            attempt.answer = answer
            attempt.correct = answer == attempt.exercise_data["correct_answer"]
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=["answer", "correct", "completed_at"])
            return Response(attempt_payload(attempt))
