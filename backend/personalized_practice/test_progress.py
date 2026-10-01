from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .progress import ProgressView, progress_for


class ProgressTests(SimpleTestCase):
    def summarize(self, attempts):
        with patch("personalized_practice.progress.ProgressAttempt.objects") as objects:
            objects.filter.return_value.order_by.return_value = attempts
            return progress_for(SimpleNamespace(pk=1))

    def attempt(self, days_ago, correct, skill="Reading fluency"):
        return SimpleNamespace(created_at=timezone.now() - timedelta(days=days_ago), correct=correct, skill=skill)

    def test_new_learner_has_no_demo_data(self):
        progress = self.summarize([])
        self.assertEqual(progress["exercisesCompleted"], 0)
        self.assertEqual(progress["currentStreak"], 0)
        self.assertEqual(progress["skills"], [])
        self.assertEqual(len(progress["history"]), 42)
        self.assertTrue(all(day["accuracy"] is None for day in progress["history"]))

    def test_accuracy_counts_incorrect_answers_and_streak_counts_days(self):
        progress = self.summarize([
            self.attempt(2, True), self.attempt(1, False),
            self.attempt(0, True), self.attempt(0, False),
        ])
        self.assertEqual(progress["exercisesCompleted"], 4)
        self.assertEqual(progress["currentStreak"], 3)
        self.assertEqual(progress["skills"][0]["progress"], 50)
        self.assertEqual(progress["history"][-1]["accuracy"], 50)
        self.assertEqual(progress["history"][-1]["completed"], 2)
        self.assertEqual(len(progress["achievements"]), 1)

    def test_streak_can_end_yesterday_but_breaks_after_a_missed_day(self):
        self.assertEqual(self.summarize([self.attempt(1, True)])["currentStreak"], 1)
        self.assertEqual(self.summarize([self.attempt(2, True)])["currentStreak"], 0)

    def test_submission_is_scoped_to_authenticated_user_and_idempotency_key(self):
        user = SimpleNamespace(pk=1, is_authenticated=True, is_learner=True)
        client_id = uuid4()
        request = APIRequestFactory().post("/api/practice/progress/", {
            "client_id": str(client_id), "exercise_id": "1", "skill": "Reading fluency",
            "correct": True, "response_time": 1000, "user": 999,
        }, format="json")
        force_authenticate(request, user=user)
        with patch("personalized_practice.progress.ProgressAttempt.objects") as objects:
            objects.filter.return_value.order_by.return_value = []
            response = ProgressView.as_view()(request)
            self.assertEqual(response.status_code, 200)
            kwargs = objects.get_or_create.call_args.kwargs
            self.assertEqual(kwargs["user"], user)
            self.assertEqual(kwargs["client_id"], client_id)
            self.assertNotIn("user", kwargs["defaults"])

    def test_progress_requires_authentication(self):
        response = ProgressView.as_view()(APIRequestFactory().get("/api/practice/progress/"))
        self.assertEqual(response.status_code, 401)
