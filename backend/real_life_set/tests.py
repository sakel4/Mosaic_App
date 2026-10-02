from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from bedrock import BedrockNotConfigured
from user.models import Profile, Skill, User

from . import generation
from .models import RealLifeSet, RealLifeSetEvaluation, RealLifeSetExercise


def exercise(**overrides):
    base = {
        "title": "Money — Change",
        "context": "AT A CAFÉ",
        "information": ["You pay £10.", "Food costs £6.50."],
        "question": "How much change do you get?",
        "options": ["£2.50", "£3.50", "£4.50"],
        "correct_answer": ["£3.50"],
    }
    return {**base, **overrides}


def reply(count=3, **overrides):
    return {"category": "Money & Shopping", "exercises": [exercise(**overrides) for _ in range(count)]}


class RealLifeSetViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="rl@example.com", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _profile(self, age_group="12_15"):
        return Profile.objects.create(
            user=self.user, age_group=age_group, interests=["football"], skills=Skill.objects.create(spelling=40)
        )

    def test_post_requires_authentication(self):
        self.assertEqual(APIClient().post("/api/real_life_set/").status_code, 401)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get("/api/real_life_set/").status_code, 405)

    def test_post_without_age_group_is_a_conflict(self):
        self.assertEqual(self.client.post("/api/real_life_set/").status_code, 409)

    def test_post_generates_saves_and_returns_the_set_without_answers(self):
        self._profile()
        with patch.object(generation, "converse_json", return_value=reply()) as mocked:
            response = self.client.post("/api/real_life_set/")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(list(body), ["id", "category", "age_group"])
        self.assertEqual((list(body["age_group"]), body["category"]), (["12_15"], "Money & Shopping"))
        exercises = body["age_group"]["12_15"]
        self.assertEqual(len(exercises), 3)
        self.assertEqual(
            list(exercises[0]), ["id", "title", "context", "information", "question", "options", "correct_answer"]
        )
        self.assertEqual(exercises[0]["correct_answer"], ["£3.50"])
        self.assertEqual(RealLifeSet.objects.count(), 1)
        saved = RealLifeSetExercise.objects.first()
        self.assertEqual(saved.correct_answer, ["£3.50"])
        self.assertIn("REAL_LIFE_EXERCISES", mocked.call_args.kwargs["system"])
        self.assertIn("Everyday Life & Dyslexia", mocked.call_args.kwargs["system"])
        self.assertIn("football", mocked.call_args.args[0])

    def test_invalid_model_output_saves_nothing(self):
        self._profile()
        with patch.object(generation, "converse_json", return_value=reply(count=2)):
            response = self.client.post("/api/real_life_set/")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(RealLifeSet.objects.count(), 0)

    def test_not_configured_returns_503(self):
        self._profile()
        with patch.object(generation, "converse_json", side_effect=BedrockNotConfigured("x")):
            self.assertEqual(self.client.post("/api/real_life_set/").status_code, 503)


class RealLifeGenerationTests(TestCase):
    def parse(self, **overrides):
        return generation._parse_exercise(exercise(**overrides), 1)

    def test_answer_must_be_one_of_the_options(self):
        with self.assertRaises(generation.RealLifeGenerationError):
            self.parse(correct_answer=["£9.99"])

    def test_answer_matching_ignores_case_and_uses_the_option_text(self):
        self.assertEqual(self.parse(options=["Aisle 1", "Aisle 2"], correct_answer="aisle 2")["correct_answer"], ["Aisle 2"])

    def test_duplicate_options_are_rejected(self):
        with self.assertRaises(generation.RealLifeGenerationError):
            self.parse(options=["Yes", "yes", "No"], correct_answer=["Yes"])

    def test_overlong_title_is_rejected(self):
        with self.assertRaises(generation.RealLifeGenerationError):
            self.parse(title="x" * 256)

    def test_19_plus_uses_the_18_plus_examples_in_the_prompt(self):
        prompt = generation.build_system_prompt({"age_groups": {}}, "19_plus")
        self.assertIn('"18_plus"', prompt)

    def test_retries_then_succeeds(self):
        with patch.object(generation, "converse_json", side_effect=[reply(count=1), reply()]) as mocked:
            real_life_set = generation.generate_real_life_set(age_group="16_18")
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(real_life_set.exercises.count(), 3)


class EvaluateRealLifeSetViewTests(TestCase):
    URL = "/api/real_life_set/evaluate/"

    def setUp(self):
        self.user = User.objects.create_user(email="ev@example.com", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.set = RealLifeSet.objects.create(id="set1", age_group="12_15", category="Money")
        for n in (1, 2, 3):
            RealLifeSetExercise.objects.create(
                id=f"set1_0{n}", real_life_set=self.set, title="t", context="c", question="q", options=["a", "b"]
            )

    def post(self, body):
        return self.client.post(self.URL, body, format="json")

    def test_requires_authentication(self):
        self.assertEqual(APIClient().post(self.URL, {}, format="json").status_code, 401)

    def test_saves_the_evaluation_and_returns_the_score(self):
        answers = {"set1_01": True, "set1_02": False, "set1_03": True}
        response = self.post({"real_life_set_id": "set1", "answers": answers})

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.json()["correct"], response.json()["total"]), (2, 3))
        saved = RealLifeSetEvaluation.objects.get(pk=response.json()["id"])
        self.assertEqual((saved.user, saved.real_life_set, saved.answers), (self.user, self.set, answers))

    def test_unknown_set_is_404(self):
        self.assertEqual(self.post({"real_life_set_id": "nope", "answers": {"x": True}}).status_code, 404)

    def test_exercise_from_another_set_is_rejected(self):
        response = self.post({"real_life_set_id": "set1", "answers": {"other_01": True}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(RealLifeSetEvaluation.objects.count(), 0)

    def test_non_boolean_or_empty_answers_are_rejected(self):
        self.assertEqual(self.post({"real_life_set_id": "set1", "answers": {"set1_01": "maybe"}}).status_code, 400)
        self.assertEqual(self.post({"real_life_set_id": "set1", "answers": {}}).status_code, 400)
