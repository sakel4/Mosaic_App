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
