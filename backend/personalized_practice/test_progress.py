from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .progress import ProgressView, progress_for


@override_settings(REAL_LIFE_TIME_ZONE="Europe/Athens")
class ProgressTests(SimpleTestCase):
    def setUp(self):
        real_life = patch("personalized_practice.progress.RealLifeExerciseAttempt.objects")
        self.real_life = real_life.start()
        self.real_life.filter.return_value = []
        self.addCleanup(real_life.stop)
        profile = patch("personalized_practice.progress.Profile.objects")
        self.profiles = profile.start()
        self.profiles.select_related.return_value.filter.return_value.first.return_value = None
        self.addCleanup(profile.stop)
        histories = patch("personalized_practice.progress.SkillHistory.objects")
        self.histories = histories.start()
        self.histories.filter.return_value.order_by.return_value = []
        self.addCleanup(histories.stop)
        baselines = patch("personalized_practice.progress.LearnerSkillBaseline.objects")
        self.baselines = baselines.start()
        self.baselines.filter.return_value = []
        self.addCleanup(baselines.stop)
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

    def test_real_life_is_counted_without_frontend_progress_submission(self):
        self.real_life.filter.return_value = [SimpleNamespace(completed_at=timezone.now(), correct=True)]
        progress = self.summarize([self.attempt(0, False)])
        self.assertEqual(progress["exercisesCompleted"], 2)
        self.assertEqual(progress["history"][-1]["accuracy"], 50)
        self.assertEqual({row["name"] for row in progress["skills"]}, {"Everyday reading", "Reading fluency"})

    def test_unscored_completions_earn_stars_without_lowering_accuracy(self):
        progress = self.summarize([self.attempt(0, None), self.attempt(0, True)])
        self.assertEqual(progress["exercisesCompleted"], 2)
        self.assertEqual(progress["history"][-1]["accuracy"], 100)
        progress = self.summarize([self.attempt(0, None)])
        self.assertEqual(progress["exercisesCompleted"], 1)
        self.assertIsNone(progress["history"][-1]["accuracy"])
        self.assertEqual(progress["skills"], [])

    def test_saved_evaluation_scores_and_previous_history_are_displayed(self):
        from .progress import SKILL_FIELDS
        values = {field: None for field in SKILL_FIELDS}
        values["reading_fluency"] = 72
        self.profiles.select_related.return_value.filter.return_value.first.return_value = SimpleNamespace(skills=SimpleNamespace(**values))
        self.histories.filter.return_value.order_by.return_value = [SimpleNamespace(**values), SimpleNamespace(**(values | {"reading_fluency": 65}))]
        progress = self.summarize([])
        self.assertEqual(progress["skills"], [{"id": 1, "name": "Reading fluency", "progress": 72, "change": 7, "metric": "score"}])
        self.assertEqual(progress["exercisesCompleted"], 0)

    def test_midnight_uses_the_same_timezone_as_real_life(self):
        now = datetime(2026, 10, 2, 21, 5, tzinfo=dt_timezone.utc)
        with patch("personalized_practice.progress.timezone.now", return_value=now):
            progress = self.summarize([SimpleNamespace(created_at=now, skill="reading_fluency", correct=True)])
        self.assertEqual(progress["history"][-1]["date"], "2026-10-03")
        self.assertEqual(progress["history"][-1]["completed"], 1)

    def test_hourly_buckets_use_local_time_and_exclude_unscored_accuracy(self):
        now = datetime(2026, 10, 2, 12, tzinfo=dt_timezone.utc)
        events = [SimpleNamespace(created_at=now, skill="spelling", correct=True),
                  SimpleNamespace(created_at=now + timedelta(minutes=10), skill="spelling", correct=None),
                  SimpleNamespace(created_at=now + timedelta(hours=2), skill="spelling", correct=False)]
        with patch("personalized_practice.progress.timezone.now", return_value=now + timedelta(hours=3)):
            progress = self.summarize(events)
        self.assertEqual(progress["hourlyHistory"], [
            {"date": "2026-10-02", "hour": 15, "completed": 2, "accuracy": 100},
            {"date": "2026-10-02", "hour": 17, "completed": 1, "accuracy": 0},
        ])
        self.assertEqual(progress["timeZone"], "Europe/Athens")
