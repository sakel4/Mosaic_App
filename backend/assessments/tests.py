import copy
import json
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from .models import Assessment, AssessmentExcercise
from .utils import InvalidAssessmentError, insert_assessment

SAMPLE_PATH = Path(settings.BASE_DIR) / "Exercises-AI" / "sample_ai_assessment.json"


def load_sample():
    """Wrap the single generated exercise in sample_ai_assessment.json as a one-exercise assessment."""
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    exercise = raw["exercise"]
    return {
        "assessment": {
            "age_group": raw["age_group"],
            "assessment_type": "exercise",
            "excercises": [
                {
                    "position": 1,
                    "kind": raw["target_skill"],
                    "skill": raw["target_skill"],
                    "difficulty": raw["difficulty"],
                    "response_type": raw["response_type"],
                    "instruction": exercise["instructions"],
                    "content_data": exercise["content_data"],
                }
            ],
        }
    }


class InsertAssessmentTests(TestCase):
    def test_inserts_assessment_and_exercises(self):
        assessment = insert_assessment(load_sample())

        saved = Assessment.objects.get(pk=assessment.pk)
        self.assertEqual(saved.age_group, "19_plus")
        self.assertEqual(saved.assessment_type, "exercise")
        exercises = list(saved.excercises.order_by("position"))
        self.assertEqual([e.position for e in exercises], [1])
        self.assertEqual(exercises[0].skill, "comprehension")
        self.assertEqual(exercises[0].difficulty_level, 4)
        self.assertEqual(exercises[0].content_data["items"][0]["id"], "item_201")

    def test_accepts_inner_assessment_object(self):
        assessment = insert_assessment(load_sample()["assessment"])
        self.assertEqual(assessment.excercises.count(), 1)

    def test_rejects_invalid_age_group(self):
        data = load_sample()
        data["assessment"]["age_group"] = "nope"
        with self.assertRaises(InvalidAssessmentError):
            insert_assessment(data)

    def test_invalid_exercise_saves_nothing(self):
        data = load_sample()
        data["assessment"]["excercises"][0]["skill"] = "not_a_skill"
        with self.assertRaises(InvalidAssessmentError):
            insert_assessment(data)
        self.assertEqual(Assessment.objects.count(), 0)
        self.assertEqual(AssessmentExcercise.objects.count(), 0)

    def test_inserts_real_structure_files(self):
        files = sorted((Path(settings.BASE_DIR) / "Exercises-AI").glob("structure_*.json"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(file=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                assessment = insert_assessment(payload)
                self.assertEqual(
                    assessment.excercises.count(),
                    len(payload["assessment"]["excercises"]),
                )


class EvaluateAssessmentTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from user.models import Profile, Skill, User

        self.user = User.objects.create_user(email="learner@example.com", password="pw")
        self.skills = Skill.objects.create(spelling=90, comprehension=50)
        Profile.objects.create(user=self.user, age_group="19_plus", skills=self.skills)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _post(self, assessment, reply):
        from unittest.mock import patch

        with patch("assessments.evaluation.converse_json", return_value=reply) as mocked:
            response = self.client.post(
                "/api/assessments/evaluate/",
                {"assessment_id": str(assessment.pk), "is_initial": False, "answers": {"item_201": {"answer": "opt_2"}}},
                format="json",
            )
        return response, mocked

    def test_assessment_type_sets_scores_without_current_skills(self):
        assessment = insert_assessment(load_sample()["assessment"] | {"assessment_type": "assessment"})
        response, mocked = self._post(
            assessment, {"skills": {"comprehension": 72.5, "bogus": 5}, "error_types": ["inference"]}
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertNotIn("current_skills", json.loads(mocked.call_args.args[0]))
        self.skills.refresh_from_db()
        self.assertEqual(float(self.skills.comprehension), 72.5)
        self.assertEqual(float(self.skills.spelling), 90)

    def test_other_types_send_current_skills_and_limit_the_change(self):
        assessment = insert_assessment(load_sample()["assessment"])
        response, mocked = self._post(assessment, {"skills": {"spelling": 10, "comprehension": 55}})

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(json.loads(mocked.call_args.args[0])["current_skills"]["spelling"], 90.0)
        self.skills.refresh_from_db()
        self.assertEqual(float(self.skills.spelling), 80)
        self.assertEqual(float(self.skills.comprehension), 55)

    def test_invalid_model_output_saves_nothing(self):
        from .models import AssessmentEvaluation

        assessment = insert_assessment(load_sample()["assessment"])
        response, _ = self._post(assessment, {"skills": {}})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(AssessmentEvaluation.objects.count(), 0)


class GenerateAssessmentTests(TestCase):
    def test_accepts_correctly_spelled_exercises_key(self):
        from unittest.mock import patch

        from user.models import User

        from . import generation

        user = User.objects.create_user(email="gen@example.com", password="pw")
        reply = load_sample()
        exercise = reply["assessment"]["excercises"][0]
        reply["assessment"]["exercises"] = [dict(exercise, skill="comprehension") for _ in range(generation.EXERCISE_COUNT)]
        del reply["assessment"]["excercises"]
        with patch.object(generation, "_reference_assessments", return_value=[{}]), patch.object(
            generation, "converse_json", return_value=reply
        ):
            assessment = generation.generate_assessment(
                assessment_type="exercise", age_group="19_plus", skills={"comprehension": 30}, user=user
            )
        self.assertEqual(assessment.user, user)
        self.assertEqual(assessment.excercises.count(), generation.EXERCISE_COUNT)


class ExercisePlanTests(TestCase):
    SCORES = {"decoding": 20.0, "spelling": 45.0, "comprehension": 60.0, "working_memory": 85.0}

    def test_seven_exercises_split_60_25_15(self):
        from . import generation

        plan = generation.build_exercise_plan(self.SCORES, {"spelling": 6})
        self.assertEqual([e["position"] for e in plan], list(range(1, 8)))
        roles = [e["role"] for e in plan]
        self.assertEqual((roles.count("weakest"), roles.count("improving"), roles.count("maintenance")), (4, 2, 1))
        skills = {e["role"]: e["skill"] for e in plan}
        self.assertEqual(skills, {"weakest": "decoding", "improving": "spelling", "maintenance": "working_memory"})

    def test_improving_defaults_when_there_is_no_history(self):
        from . import generation

        plan = generation.build_exercise_plan(self.SCORES, {})
        self.assertEqual({e["role"]: e["skill"] for e in plan}["improving"], "spelling")

    def test_single_skill_still_fills_every_slot(self):
        from . import generation

        plan = generation.build_exercise_plan({"spelling": 30.0}, {})
        self.assertEqual(len(plan), 7)
        self.assertEqual({e["skill"] for e in plan}, {"spelling"})

    def test_wrong_exercise_count_is_rejected(self):
        from unittest.mock import patch

        from . import generation

        reply = load_sample()
        with patch.object(generation, "_reference_assessments", return_value=[{}]), patch.object(
            generation, "converse_json", return_value=reply
        ):
            with self.assertRaises(generation.AssessmentGenerationError):
                generation.generate_assessment(
                    assessment_type="exercise", age_group="19_plus", skills={"comprehension": 30}
                )
        self.assertEqual(Assessment.objects.count(), 0)

    def test_improvement_uses_recent_skill_snapshots(self):
        from user.models import User

        from . import generation
        from .models import AssessmentEvaluation, SkillHistory

        user = User.objects.create_user(email="trend@example.com", password="pw")
        assessment = insert_assessment(load_sample()["assessment"])
        for value in (40, 55):
            history = SkillHistory.objects.create(spelling=value, comprehension=70)
            AssessmentEvaluation.objects.create(assessment=assessment, user_id=user, updated_skills=history)
        change = generation._improvement(user, {"spelling": 55.0, "comprehension": 70.0})
        self.assertEqual(change, {"spelling": 15.0, "comprehension": 0.0})

    def test_exercise_with_the_wrong_skill_is_rejected(self):
        from unittest.mock import patch

        from . import generation

        reply = load_sample()
        exercise = reply["assessment"]["excercises"][0]
        reply["assessment"]["excercises"] = [dict(exercise, skill="spelling") for _ in range(7)]
        with patch.object(generation, "_reference_assessments", return_value=[{}]), patch.object(
            generation, "converse_json", return_value=reply
        ):
            with self.assertRaises(generation.AssessmentGenerationError):
                generation.generate_assessment(
                    assessment_type="exercise", age_group="19_plus", skills={"comprehension": 30}
                )
        self.assertEqual(Assessment.objects.count(), 0)


class PhonemeOptionsTests(TestCase):
    def _generate(self, kind, skill, assessment_type="exercise"):
        from unittest.mock import patch

        from . import generation

        exercise = {
            "position": 1,
            "kind": kind,
            "skill": skill,
            "difficulty": 3,
            "response_type": "single_choice_set",
            "instruction": "x",
            "content_data": {
                "items": [
                    {
                        "id": "a",
                        "audio_prompt": "Say triple in your head. Remove the first /t/ sound.",
                        "options": [{"id": "1", "text": "triple"}, {"id": "2", "text": "/t/ /r/ /i/"}],
                    }
                ]
            },
            "answers": {"a": "1"},
        }
        reply = {"assessment": {"age_group": "19_plus", "excercises": [copy.deepcopy(exercise) for _ in range(7)]}}
        with patch.object(generation, "_reference_assessments", return_value=[{}]), patch.object(
            generation, "converse_json", return_value=reply
        ), patch.object(generation, "build_exercise_plan", return_value=[
            {"position": n, "skill": skill, "role": "weakest"} for n in range(1, 8)
        ]):
            assessment = generation.generate_assessment(
                assessment_type=assessment_type, age_group="19_plus", skills={skill: 30}
            )
        return assessment.excercises.order_by("position").first().content_data["items"][0]["options"]

    def test_first_letter_is_removed_for_phoneme_manipulation_of_phonological_awareness(self):
        options = self._generate("phoneme_manipulation", "phonological_awareness")
        self.assertEqual([o["text"] for o in options], ["riple", "/t/ /r/ /i/"])

    def test_other_kinds_and_skills_are_left_alone(self):
        options = self._generate("spelling", "spelling")
        self.assertEqual(options[0]["text"], "triple")

    def test_other_assessment_types_are_left_alone(self):
        options = self._generate("phoneme_manipulation", "phonological_awareness", assessment_type="real_life")
        self.assertEqual(options[0]["text"], "triple")
