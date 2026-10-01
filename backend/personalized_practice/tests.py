import unittest
import json
import os
from unittest.mock import Mock, patch

from personalized_practice.bank import load_age_bank, public_seed, select_seed
from personalized_practice.domain import LearnerContext, SkillEvidence
from personalized_practice.generator import BedrockExerciseGenerator, _describe_shape
from personalized_practice.orchestrator import PracticeOrchestrator
from personalized_practice.selection import age_group_for_age, choose_target_skill, difficulty_for_score


class PersonalizationTests(unittest.TestCase):
    def test_age_band_boundaries(self):
        cases = [(11, "under_12"), (12, "12_15"), (15, "12_15"), (16, "16_18"), (18, "16_18"), (19, "19_plus")]
        for age, expected in cases:
            with self.subTest(age=age):
                self.assertEqual(age_group_for_age(age), expected)

    def test_each_fixed_bank_loads_with_matching_age_group(self):
        for age_group in ("under_12", "12_15", "16_18", "19_plus"):
            with self.subTest(age_group=age_group):
                self.assertEqual(load_age_bank(age_group)["age_group"], age_group)

    def test_seed_redacts_answer_material_recursively(self):
        seed = public_seed(
            {
                "id": "seed",
                "kind": "choice",
                "skill": "comprehension",
                "difficulty": 2,
                "response_type": "single_choice_set",
                "content_data": {"items": [{"correct_option_id": "b", "options": ["a", "b"]}]},
                "private_scoring": {"answers": {"q1": "b"}},
            }
        )
        self.assertNotIn("private_scoring", seed)
        self.assertNotIn("correct_option_id", seed["content_data"]["items"][0])

    def test_generation_blueprint_contains_shape_not_assessment_text(self):
        shape = _describe_shape({"prompt": "private assessment prompt", "items": ["test word"]})
        self.assertEqual(shape, {"prompt": "string", "items": {"type": "array", "length": 1, "items": "string"}})

    @patch.dict(
        os.environ,
        {
            "BEDROCK_MODEL_ID": "zai.glm-4.7-flash",
            "AWS_DEFAULT_REGION": "eu-west-1",
        },
    )
    def test_bedrock_generator_uses_converse_and_parses_json(self):
        generated = {
            "title": "Practice",
            "instructions": "Complete the task.",
            "prompt": "Try this.",
            "content_data": {"items": []},
            "private_scoring": {"answer_key": {"item": "a"}, "error_types": []},
        }
        client = Mock()
        client.converse.return_value = {
            "output": {"message": {"content": [{"text": json.dumps(generated)}]}}
        }
        result = BedrockExerciseGenerator(client).generate(
            age_group="12_15",
            skill="spelling",
            difficulty=2,
            seed={"id": "seed", "kind": "spelling", "response_type": "typed_text", "content_data": {}},
            recent_exercises=(),
        )
        self.assertEqual(result, generated)
        self.assertEqual(client.converse.call_args.kwargs["modelId"], "zai.glm-4.7-flash")

    def test_decoding_selects_combined_word_reading_seed(self):
        seed = select_seed("12_15", "decoding", set())
        self.assertEqual(seed["skill"], "decoding_and_word_recognition")
        self.assertNotIn("private_scoring", seed)

    def test_selection_ignores_skills_missing_from_the_age_bank(self):
        context = LearnerContext(
            14,
            {
                "naming_speed": SkillEvidence(10, 1.0, True),
                "comprehension": SkillEvidence(60, 0.8, True),
            },
        )
        self.assertEqual(choose_target_skill(context, {"comprehension"}), "comprehension")

    def test_proposal_rotation_chooses_weak_improving_then_maintenance(self):
        skills = {
            "decoding": SkillEvidence(30, 0.9, True, "stable", {"substitution": 3}),
            "spelling": SkillEvidence(45, 0.8, True, "improving"),
            "comprehension": SkillEvidence(82, 0.9, True, "stable"),
        }
        self.assertEqual(choose_target_skill(LearnerContext(14, skills, 0)), "decoding")
        self.assertEqual(choose_target_skill(LearnerContext(14, skills, 12)), "spelling")
        self.assertEqual(choose_target_skill(LearnerContext(14, skills, 17)), "comprehension")

    def test_proposal_difficulty_bands_adjust_and_cap_seed_difficulty(self):
        self.assertEqual(difficulty_for_score(25, 3), 2)
        self.assertEqual(difficulty_for_score(50, 3), 3)
        self.assertEqual(difficulty_for_score(70, 3), 4)
        self.assertEqual(difficulty_for_score(90, 4), 5)

    def test_orchestrator_persists_private_scoring_but_does_not_return_it(self):
        class Repository:
            saved = None

            def get_context(self, user_id):
                return LearnerContext(14, {"decoding": SkillEvidence(30, 0.9, True)})

            def save_exercise(self, user_id, record):
                self.saved = record

        class Generator:
            def generate(self, **kwargs):
                return {
                    "title": "Practice",
                    "instructions": "Read the item.",
                    "prompt": "Choose one.",
                    "content_data": {
                        "correct_answer": "hidden",
                        "correct_option_id": "b",
                        "options": ["a", "b"],
                    },
                    "private_scoring": {"answer_key": "hidden", "error_types": []},
                }

        repository = Repository()
        result = PracticeOrchestrator(repository, Generator()).next_exercise("learner-1")
        self.assertIn("private_scoring", repository.saved)
        self.assertNotIn("private_scoring", result)
        self.assertNotIn("correct_answer", result["exercise"]["content_data"])
        self.assertNotIn("correct_option_id", result["exercise"]["content_data"])


if __name__ == "__main__":
    unittest.main()
