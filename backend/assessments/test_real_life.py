from datetime import datetime, timedelta, timezone
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from user.models import User
from .models import RealLifeExercise, RealLifeExerciseAttempt


@override_settings(REAL_LIFE_TIME_ZONE="Europe/Athens")
class DailyRealLifeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="daily@example.com", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.now = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
        clock = patch("assessments.real_life.timezone.now", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        # Profile lookup is independent of the daily assignment/completion records.
        profile = patch("assessments.real_life.Profile.objects.filter")
        self.profile = profile.start()
        self.profile.return_value.first.return_value = SimpleNamespace(age_group="under_12")
        self.addCleanup(profile.stop)
        for index in range(6):
            RealLifeExercise.objects.create(
                id=f"u12_{index}", age_group="under_12", title="Getting ready", context="GETTING READY",
                information=["Leave at 3:30 PM."], question="What should you do now?",
                options=["Get ready", "Go to bed"], correct_answer="Get ready",
            )

    def daily(self):
        return self.client.get("/api/assessments/real_life/daily/")

    def complete(self, attempt, answer="Get ready"):
        return self.client.post(f"/api/assessments/real_life/{attempt['attempt_id']}/complete/", {"answer": answer}, format="json")

    def test_same_three_exercises_on_refresh_without_leaking_answers(self):
        first = self.daily()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.data["exercises"]), 3)
        self.assertEqual(first.data, self.daily().data)
        self.assertEqual(RealLifeExerciseAttempt.objects.count(), 3)
        self.assertNotIn("correct_answer", first.data["exercises"][0]["exercise"])
        self.assertIsNone(first.data["exercises"][0]["correct_answer"])

    def test_three_completions_lock_day_and_retry_does_not_overwrite_answer(self):
        exercises = self.daily().data["exercises"]
        for exercise in exercises:
            response = self.complete(exercise, "Go to bed")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.data["correct"])
            self.assertEqual(response.data["correct_answer"], "Get ready")
        retry = self.complete(exercises[0])
        self.assertEqual(retry.data["answer"], "Go to bed")
        day = self.daily().data
        self.assertTrue(day["locked"])
        self.assertEqual(day["remaining"], 0)
        self.assertEqual(RealLifeExerciseAttempt.objects.count(), 3)

    def test_athens_midnight_unlocks_new_set_and_preserves_history(self):
        self.now = datetime(2026, 10, 2, 20, 59, tzinfo=timezone.utc)
        old = self.daily().data["exercises"]
        for exercise in old:
            self.complete(exercise)
        self.now += timedelta(minutes=1)  # Midnight in Athens (UTC+3).
        new = self.daily().data
        self.assertFalse(new["locked"])
        self.assertEqual(new["completed"], 0)
        self.assertTrue({item["exercise"]["id"] for item in old}.isdisjoint(
            {item["exercise"]["id"] for item in new["exercises"]}))
        self.assertEqual(RealLifeExerciseAttempt.objects.filter(completed_at__isnull=False).count(), 3)

    def test_unfinished_yesterday_exercise_expires(self):
        old = self.daily().data["exercises"][0]
        self.now += timedelta(days=1)
        self.assertEqual(self.complete(old).status_code, 409)

    def test_invalid_answers_and_other_users_cannot_complete(self):
        exercise = self.daily().data["exercises"][0]
        self.assertEqual(self.complete(exercise, "Invented option").status_code, 400)
        other = User.objects.create_user(email="other@example.com", password="pw")
        self.client.force_authenticate(other)
        self.assertEqual(self.complete(exercise).status_code, 404)
        self.assertFalse(RealLifeExerciseAttempt.objects.filter(completed_at__isnull=False).exists())

    def test_requires_authentication(self):
        self.client = APIClient()
        self.assertEqual(self.daily().status_code, 401)

    def test_requires_age_group_and_sufficient_bank(self):
        self.profile.return_value.first.return_value = None
        self.assertEqual(self.daily().status_code, 409)
        self.profile.return_value.first.return_value = SimpleNamespace(age_group="19_plus")
        self.assertEqual(self.daily().status_code, 409)
        self.assertEqual(RealLifeExerciseAttempt.objects.count(), 0)

    def test_import_bank_is_repeatable(self):
        call_command("load_real_life_exercises", stdout=StringIO())
        count = RealLifeExercise.objects.count()
        call_command("load_real_life_exercises", stdout=StringIO())
        self.assertEqual(RealLifeExercise.objects.count(), count)
        for exercise in RealLifeExercise.objects.all():
            self.assertIn(exercise.correct_answer, exercise.options)
