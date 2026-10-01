import unittest
import json
import io
import os
import wave
from unittest.mock import AsyncMock, Mock, patch

from amazon_transcribe.model import Alternative, Item, Result, Transcript, TranscriptEvent

from personalized_practice.bank import load_age_bank, public_seed, select_seed
from personalized_practice.assessment import AssessmentSubmissionError, score_assessment
from personalized_practice.domain import LearnerContext, PracticeDataError, SkillEvidence
from personalized_practice.generator import (
    BedrockExerciseGenerator,
    ExerciseGenerationError,
    _describe_shape,
    _normalize_private_scoring,
    _parse_json_object,
)
from personalized_practice.orchestrator import PracticeOrchestrator
from personalized_practice.selection import (
    age_group_for_age,
    choose_secondary_skill,
    choose_target_skill,
    difficulty_for_score,
    skill_priority,
)
from personalized_practice.speech_scoring import (
    SpeechScoringError,
    TranscribeSpeechScorer,
    score_transcription,
)


class PersonalizationTests(unittest.TestCase):
    @staticmethod
    def _transcribe_result(words, confidence="0.95"):
        return {
            "results": {
                "items": [
                    {
                        "type": "pronunciation",
                        "alternatives": [{"content": word, "confidence": confidence}],
                    }
                    for word in words
                ]
            }
        }

    def test_transcribe_alignment_splits_correct_and_attempted_word_counts(self):
        exercise = next(
            item for item in load_age_bank("19_plus")["exercises"]
            if item["kind"] == "word_reading_sample"
        )
        transcription = self._transcribe_result([
            "relvicate", "monestral", "preficiant", "clostering", "subrenity",
            "receipt", "maintenance", "schedule", "colleague",
        ])
        result = score_transcription(exercise, transcription)
        self.assertEqual(result["scores"]["pseudowords"]["correct"], 4)
        self.assertEqual(result["scores"]["pseudowords"]["attempted"], 5)
        self.assertEqual(result["scores"]["real_words"]["correct"], 4)
        self.assertEqual(result["scores"]["real_words"]["attempted"], 4)

    def test_transcribe_alignment_does_not_count_unreached_words_as_attempted(self):
        exercise = next(
            item for item in load_age_bank("19_plus")["exercises"]
            if item["kind"] == "word_reading_sample"
        )
        transcription = self._transcribe_result([
            "relvicate", "monestral", "preficient", "clostering", "subrenity",
        ])
        result = score_transcription(exercise, transcription)
        self.assertEqual(result["scores"]["pseudowords"]["attempted"], 5)
        self.assertEqual(result["scores"]["real_words"]["attempted"], 0)

    @staticmethod
    def _wav_audio(sample_rate=16000, seconds=1):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(sample_rate)
            recording.writeframes(b"\x00\x00" * sample_rate * seconds)
        return io.BytesIO(buffer.getvalue())

    @patch("personalized_practice.speech_scoring.signing.dumps", return_value="signed-result")
    def test_transcribe_stream_scores_wav_and_returns_signed_results(self, _sign):
        bank = load_age_bank("19_plus")
        exercise = next(item for item in bank["exercises"] if item["kind"] == "word_reading_sample")
        target_words = [word for section in exercise["content_data"]["sections"] for word in section["items"]]
        transcription = self._transcribe_result(target_words)

        def transcript_event(words, is_partial):
            items = [
                Item(item_type="pronunciation", content=word, confidence=0.95)
                for word in words
            ]
            alternative = Alternative(" ".join(words), items, [])
            return TranscriptEvent(Transcript([Result(is_partial=is_partial, alternatives=[alternative])]))

        class FakeInputStream:
            def __init__(self):
                self.chunks = []
                self.ended = False

            async def send_audio_event(self, audio_chunk):
                self.chunks.append(audio_chunk)

            async def end_stream(self):
                self.ended = True

        class FakeOutputStream:
            async def __aiter__(self):
                yield transcript_event(["incorrect-partial"], True)
                yield transcript_event(target_words, False)

        class FakeClient:
            def __init__(self):
                self.stream = Mock()
                self.stream.input_stream = FakeInputStream()
                self.stream.output_stream = FakeOutputStream()

            async def start_stream_transcription(self, **kwargs):
                self.kwargs = kwargs
                return self.stream

        client = FakeClient()
        service = TranscribeSpeechScorer(streaming_client=client)
        with patch("personalized_practice.speech_scoring.asyncio.sleep", new=AsyncMock()):
            result = service.score_audio(
                "learner-id",
                "19_plus",
                bank["assessment_version"],
                exercise["id"],
                self._wav_audio(),
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["speech_result_token"], "signed-result")
        self.assertEqual(result["scores"]["pseudowords"]["correct"], 5)
        self.assertEqual(result["scores"]["real_words"]["correct"], 4)
        self.assertEqual(len(client.stream.input_stream.chunks), 10)
        self.assertTrue(all(len(chunk) == 3200 for chunk in client.stream.input_stream.chunks))
        self.assertTrue(client.stream.input_stream.ended)
        self.assertEqual(client.kwargs["media_sample_rate_hz"], 16000)
        self.assertEqual(client.kwargs["media_encoding"], "pcm")

    def test_transcribe_stream_rejects_audio_not_in_required_pcm_format(self):
        bank = load_age_bank("19_plus")
        service = TranscribeSpeechScorer(streaming_client=Mock())
        with self.assertRaises(SpeechScoringError):
            service.score_audio(
                "learner-id",
                "19_plus",
                bank["assessment_version"],
                "19_plus_voice_words_01",
                self._wav_audio(sample_rate=44100),
            )

    def _assessment_submission(self, overrides=None):
        bank = load_age_bank("19_plus")
        responses = [{"exercise_id": item["id"], "skipped": True} for item in bank["exercises"]]
        for exercise_id, response in (overrides or {}).items():
            next(item for item in responses if item["exercise_id"] == exercise_id).update(response)
        return {
            "assessment_version": bank["assessment_version"],
            "responses": responses,
        }

    def test_assessment_scores_answers_and_leaves_skipped_voice_skills_unscored(self):
        submission = self._assessment_submission({
            "19_plus_pa_nv_01": {"skipped": False, "answers": {"a": "1", "b": "wrong"}},
        })
        results = {item["skill"]: item for item in score_assessment("19_plus", submission)}
        self.assertEqual(results["phonological_awareness"]["baseline_score"], 50)
        self.assertEqual(results["phonological_awareness"]["confidence"], 0.42)
        self.assertIsNone(results["decoding"]["baseline_score"])
        self.assertIsNone(results["word_recognition"]["baseline_score"])
        self.assertIsNone(results["reading_fluency"]["baseline_score"])

    def test_assessment_validates_spoken_counts_and_splits_reading_skills(self):
        submission = self._assessment_submission({
            "19_plus_voice_words_01": {"skipped": False},
        })
        verified = {
            "19_plus_voice_words_01": {
                "scores": {
                    "pseudowords": {"correct": 4, "attempted": 5},
                    "real_words": {"correct": 3, "attempted": 4},
                },
                "confidence": 0.95,
            },
        }
        results = {
            item["skill"]: item
            for item in score_assessment("19_plus", submission, verified)
        }
        self.assertEqual(results["decoding"]["baseline_score"], 80)
        self.assertEqual(results["word_recognition"]["baseline_score"], 75)
        verified["19_plus_voice_words_01"]["scores"]["pseudowords"] = {
            "correct": 6,
            "attempted": 6,
        }
        with self.assertRaises(AssessmentSubmissionError):
            score_assessment("19_plus", submission, verified)

    def test_assessment_rejects_client_supplied_spoken_counts(self):
        submission = self._assessment_submission({
            "19_plus_voice_words_01": {
                "skipped": False,
                "spoken_scores": {"pseudowords": {"correct": 5, "attempted": 5}},
            },
        })
        with self.assertRaises(AssessmentSubmissionError):
            score_assessment("19_plus", submission)

    def test_assessment_rejects_unknown_items(self):
        submission = self._assessment_submission({
            "19_plus_pa_nv_01": {"skipped": False, "answers": {"not-an-item": "1"}},
        })
        with self.assertRaises(AssessmentSubmissionError):
            score_assessment("19_plus", submission)

    def test_assessment_rejects_unknown_versions(self):
        submission = self._assessment_submission()
        submission["assessment_version"] = "wrong-version"
        with self.assertRaises(AssessmentSubmissionError):
            score_assessment("19_plus", submission)

    def test_assessment_requires_boolean_skip_marker(self):
        submission = self._assessment_submission({
            "19_plus_pa_nv_01": {"skipped": 0, "answers": {"a": "1"}},
        })
        with self.assertRaises(AssessmentSubmissionError):
            score_assessment("19_plus", submission)

    def test_working_memory_awards_partial_sequence_element_credit(self):
        submission = self._assessment_submission({
            "19_plus_wm_nv_01": {
                "skipped": False,
                "answers": {"a": ["4", "9", "0", "7", "3"]},
            },
        })
        result = next(
            item for item in score_assessment("19_plus", submission)
            if item["skill"] == "working_memory"
        )
        self.assertEqual(result["baseline_score"], 80)
        self.assertEqual(result["items_attempted"], 5)
        self.assertEqual(result["items_available"], 9)

    def test_age_band_boundaries(self):
        cases = [(11, "under_12"), (12, "12_15"), (15, "12_15"), (16, "16_18"), (18, "16_18"), (19, "19_plus")]
        for age, expected in cases:
            with self.subTest(age=age):
                self.assertEqual(age_group_for_age(age), expected)

    def test_each_fixed_bank_loads_with_matching_age_group(self):
        for age_group in ("under_12", "12_15", "16_18", "19_plus"):
            with self.subTest(age_group=age_group):
                self.assertEqual(load_age_bank(age_group)["age_group"], age_group)

    def test_learner_context_accepts_only_database_age_groups(self):
        context = LearnerContext.from_mapping({"age_group": "19_plus", "skills": {}})
        self.assertEqual(context.age_group, "19_plus")
        with self.assertRaises(PracticeDataError):
            LearnerContext.from_mapping({"age_group": "adult", "skills": {}})

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

    def test_model_json_parser_accepts_wrapped_object_only(self):
        expected = {"title": "Practice", "private_scoring": {"answer_key": {"q1": "a"}}}
        wrapped = f"Here is the exercise:\n```json\n{json.dumps(expected)}\n```"
        self.assertEqual(_parse_json_object(wrapped), expected)
        with self.assertRaises(ExerciseGenerationError):
            _parse_json_object("No JSON was returned.")

    def test_private_scoring_normalizes_answer_aliases_but_requires_a_key(self):
        generated = {"private_scoring": {"answers": {"q1": "a"}}}
        _normalize_private_scoring(generated)
        self.assertEqual(generated["private_scoring"]["answer_key"], {"q1": "a"})
        self.assertEqual(generated["private_scoring"]["error_types"], [])
        with self.assertRaises(ExerciseGenerationError):
            _normalize_private_scoring({"private_scoring": {"error_types": []}})

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
        prompt = json.loads(client.converse.call_args.kwargs["messages"][0]["content"][0]["text"])
        self.assertIn("learner_profile", prompt)

    def test_decoding_selects_combined_word_reading_seed(self):
        seed = select_seed("12_15", "decoding", set())
        self.assertEqual(seed["skill"], "decoding_and_word_recognition")
        self.assertNotIn("private_scoring", seed)

    def test_selection_ignores_skills_missing_from_the_age_bank(self):
        context = LearnerContext(
            "12_15",
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
        self.assertEqual(choose_target_skill(LearnerContext("12_15", skills, 0)), "decoding")
        self.assertEqual(choose_target_skill(LearnerContext("12_15", skills, 12)), "spelling")
        self.assertEqual(choose_target_skill(LearnerContext("12_15", skills, 17)), "comprehension")

    def test_confidence_can_outweigh_a_lower_uncertain_score(self):
        skills = {
            "working_memory": SkillEvidence(35, 0.35),
            "reading_fluency": SkillEvidence(45, 0.94),
        }
        self.assertGreater(skill_priority(skills["reading_fluency"]), skill_priority(skills["working_memory"]))

    def test_direct_evidence_has_higher_priority_when_other_evidence_matches(self):
        direct = SkillEvidence(50, 0.8, direct_evidence=True)
        indirect = SkillEvidence(50, 0.8, direct_evidence=False)
        self.assertGreater(skill_priority(direct), skill_priority(indirect))

    def test_repeated_errors_raise_priority_and_secondary_prefers_improving(self):
        skills = {
            "decoding": SkillEvidence(55, 0.8, error_counts={"substitution": 4}),
            "spelling": SkillEvidence(50, 0.8, trend="improving"),
            "comprehension": SkillEvidence(30, 0.95, trend="stable"),
        }
        without_repeats = SkillEvidence(55, 0.8)
        self.assertGreater(skill_priority(skills["decoding"]), skill_priority(without_repeats))
        self.assertEqual(
            choose_secondary_skill(LearnerContext("12_15", skills), "comprehension"),
            "spelling",
        )

    def test_proposal_difficulty_bands_adjust_and_cap_seed_difficulty(self):
        self.assertEqual(difficulty_for_score(25, 3), 2)
        self.assertEqual(difficulty_for_score(50, 3), 3)
        self.assertEqual(difficulty_for_score(70, 3), 4)
        self.assertEqual(difficulty_for_score(90, 4), 5)

    def test_orchestrator_persists_private_scoring_but_does_not_return_it(self):
        class Repository:
            saved = None

            def get_context(self, user_id):
                return LearnerContext("12_15", {"decoding": SkillEvidence(30, 0.9, True)})

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

    def test_orchestrator_passes_multidimensional_profile_and_secondary_focus(self):
        class Repository:
            def get_context(self, user_id):
                return LearnerContext(
                    "19_plus",
                    {
                        "comprehension": SkillEvidence(
                            58,
                            0.82,
                            True,
                            "stable",
                            {"inference_miss": 2},
                            {"accuracy": 0.58, "response_time_ms": 4200},
                        ),
                        "spelling": SkillEvidence(70, 0.8, True, "improving"),
                    },
                )

            def save_exercise(self, user_id, record):
                pass

        class Generator:
            received = None

            def generate(self, **kwargs):
                self.received = kwargs
                return {
                    "title": "Practice",
                    "instructions": "Read the passage.",
                    "prompt": "Choose an answer.",
                    "content_data": {"items": []},
                    "private_scoring": {"answer_key": {"q1": "a"}, "error_types": []},
                }

        generator = Generator()
        PracticeOrchestrator(Repository(), generator).next_exercise("learner-1")
        self.assertEqual(generator.received["age_group"], "19_plus")
        self.assertEqual(generator.received["skill"], "comprehension")
        self.assertEqual(generator.received["secondary_skill"], "spelling")
        profile = generator.received["learner_profile"]
        self.assertEqual(profile["skills"]["comprehension"]["mastery"], 0.58)
        self.assertEqual(profile["skills"]["comprehension"]["metrics"]["response_time_ms"], 4200)
        self.assertEqual(profile["skills"]["comprehension"]["error_counts"]["inference_miss"], 2)
        self.assertNotIn("diagnosis", profile)


if __name__ == "__main__":
    unittest.main()
