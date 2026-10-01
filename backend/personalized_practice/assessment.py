import json
from collections import defaultdict
from typing import Any, Mapping

from django.db import connection, transaction

from personalized_practice.bank import load_age_bank
from personalized_practice.domain import PracticeDataError
from personalized_practice.speech_scoring import SpeechScoringError


class AssessmentSubmissionError(ValueError):
    pass


SKILL_FIELD_MAP = {
    "letter_sound": "letter_sound_association",
    "phonological_awareness": "phonological_awareness",
    "decoding": "decoding",
    "word_recognition": "word_recognition",
    "reading_fluency": "reading_fluency",
    "spelling": "spelling",
    "comprehension": "comprehension",
    "working_memory": "working_memory",
}


def _confidence(scoring: Mapping[str, Any], skill: str | None = None) -> float:
    confidence_values = []
    if skill and isinstance(scoring.get("derived_skills"), Mapping):
        derived = scoring["derived_skills"].get(skill, {})
        if isinstance(derived, Mapping) and isinstance(derived.get("confidence"), (int, float)):
            confidence_values.append(float(derived["confidence"]))
    if isinstance(scoring.get("confidence"), (int, float)):
        confidence_values.append(float(scoring["confidence"]))
    score = scoring.get("score", {})
    if isinstance(score, Mapping) and isinstance(score.get("confidence"), (int, float)):
        confidence_values.append(float(score["confidence"]))
    return min(confidence_values) if confidence_values else 0.5


def _same_answer(submitted: Any, expected: Any) -> bool:
    if isinstance(expected, str):
        return isinstance(submitted, str) and submitted.strip().casefold() == expected.strip().casefold()
    if isinstance(expected, list):
        return isinstance(submitted, list) and len(submitted) == len(expected) and all(
            _same_answer(given, answer) for given, answer in zip(submitted, expected)
        )
    return submitted == expected


def _validate_count_pair(value: Any, maximum: int, field: str) -> tuple[int, int]:
    if not isinstance(value, Mapping):
        raise AssessmentSubmissionError(f"{field} must include correct and attempted counts.")
    correct = value.get("correct")
    attempted = value.get("attempted")
    if type(correct) is not int or type(attempted) is not int:
        raise AssessmentSubmissionError(f"{field} counts must be integers.")
    if correct < 0 or attempted < 0 or correct > attempted or attempted > maximum:
        raise AssessmentSubmissionError(f"{field} counts are outside the allowed range.")
    return correct, attempted


def _result(skill: str, correct: int, attempted: int, available: int, confidence: float) -> dict[str, Any]:
    score = round(100 * correct / attempted, 2) if attempted else None
    confidence = round(confidence * attempted / available, 3) if attempted and available else 0.35
    return {
        "skill": skill,
        "baseline_score": score,
        "confidence": confidence,
        "direct_evidence": score is not None,
        "items_attempted": attempted,
        "items_available": available,
    }


def score_assessment(
    age_group: str,
    submission: Mapping[str, Any],
    verified_speech_scores: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    bank = load_age_bank(age_group)
    if submission.get("assessment_version") != bank.get("assessment_version"):
        raise AssessmentSubmissionError("Assessment version does not match the learner's age group.")

    responses = submission.get("responses")
    if not isinstance(responses, list):
        raise AssessmentSubmissionError("responses must be a list.")
    response_by_id = {}
    for response in responses:
        if not isinstance(response, Mapping) or not isinstance(response.get("exercise_id"), str):
            raise AssessmentSubmissionError("Each response must include an exercise_id.")
        exercise_id = response["exercise_id"]
        if exercise_id in response_by_id:
            raise AssessmentSubmissionError(f"Duplicate response for exercise '{exercise_id}'.")
        response_by_id[exercise_id] = response

    exercises = bank["exercises"]
    known_ids = {str(exercise["id"]) for exercise in exercises}
    unknown_ids = set(response_by_id) - known_ids
    missing_ids = known_ids - set(response_by_id)
    if unknown_ids:
        raise AssessmentSubmissionError("Submission contains an unknown exercise_id.")
    if missing_ids:
        raise AssessmentSubmissionError("Submit every exercise, marking uncompleted exercises as skipped.")

    verified_speech_scores = verified_speech_scores or {}
    scored = []
    for exercise in exercises:
        exercise_id = str(exercise["id"])
        response = response_by_id[exercise_id]
        scoring = exercise.get("private_scoring", {})
        base_confidence = _confidence(scoring)
        if exercise.get("response_type") == "spoken" and "spoken_scores" in response:
            raise AssessmentSubmissionError("Speech scores must come from the server-side transcription service.")
        skipped = response.get("skipped", False)
        if type(skipped) is not bool:
            raise AssessmentSubmissionError("skipped must be a boolean.")
        if skipped:
            skills = scoring.get("derived_skills", {})
            skill_names = list(skills) if isinstance(skills, Mapping) and skills else [str(exercise["skill"])]
            for skill in skill_names:
                scored.append(_result(skill, 0, 0, 0, 0.35))
            continue

        if exercise.get("response_type") == "spoken":
            verified = verified_speech_scores.get(exercise_id)
            if not isinstance(verified, Mapping) or not isinstance(verified.get("scores"), Mapping):
                raise AssessmentSubmissionError(f"Complete server-side speech scoring for '{exercise_id}'.")
            speech_confidence = verified.get("confidence")
            if type(speech_confidence) not in (int, float) or not 0 <= speech_confidence <= 1:
                raise AssessmentSubmissionError("Verified speech confidence is invalid.")
            spoken_scores = verified["scores"]
            derived = scoring.get("derived_skills")
            if isinstance(derived, Mapping):
                for skill, rule in derived.items():
                    section = str(rule["items"])
                    maximum = len(next(
                        item["items"] for item in exercise["content_data"]["sections"] if item["id"] == section
                    ))
                    counts = spoken_scores.get(section)
                    if counts is None:
                        scored.append(_result(str(skill), 0, 0, 0, 0.35))
                    else:
                        correct, attempted = _validate_count_pair(counts, maximum, section)
                        scored.append(_result(
                            str(skill), correct, attempted, maximum,
                            min(_confidence(scoring, str(skill)), speech_confidence),
                        ))
            else:
                lines = exercise["content_data"]["passage_lines"]
                maximum = sum(len(line.split()) for line in lines)
                counts = spoken_scores.get("reading_fluency")
                if counts is None:
                    scored.append(_result("reading_fluency", 0, 0, 0, 0.35))
                else:
                    correct, attempted = _validate_count_pair(counts, maximum, "reading_fluency")
                    scored.append(_result(
                        "reading_fluency", correct, attempted, maximum,
                        min(base_confidence, speech_confidence),
                    ))
            continue

        answer_key = scoring.get("answers")
        if not isinstance(answer_key, Mapping):
            raise AssessmentSubmissionError(f"Exercise '{exercise_id}' has no supported answer key.")
        answers = response.get("answers", {})
        if not isinstance(answers, Mapping):
            raise AssessmentSubmissionError("answers must be an object keyed by item id.")
        if set(answers) - set(answer_key):
            raise AssessmentSubmissionError(f"Response contains an unknown item for exercise '{exercise_id}'.")
        if exercise.get("skill") == "working_memory":
            if any(not isinstance(value, list) for value in answers.values()):
                raise AssessmentSubmissionError("Working-memory answers must be lists of sequence elements.")
            correct = sum(
                index < len(answers[item_id]) and _same_answer(answers[item_id][index], expected)
                for item_id, expected_sequence in answer_key.items()
                if item_id in answers
                for index, expected in enumerate(expected_sequence)
            )
            attempted = sum(len(expected_sequence) for item_id, expected_sequence in answer_key.items() if item_id in answers)
            available = sum(len(expected_sequence) for expected_sequence in answer_key.values())
            scored.append(_result(str(exercise["skill"]), correct, attempted, available, base_confidence))
            continue
        attempted = len(answers)
        correct = sum(_same_answer(value, answer_key[item_id]) for item_id, value in answers.items())
        scored.append(_result(str(exercise["skill"]), correct, attempted, len(answer_key), base_confidence))

    grouped = defaultdict(list)
    for item in scored:
        grouped[item["skill"]].append(item)
    results = []
    for skill, evidence in grouped.items():
        valid = [item for item in evidence if item["baseline_score"] is not None]
        if valid:
            score = round(sum(item["baseline_score"] for item in valid) / len(valid), 2)
            confidence = round(sum(item["confidence"] for item in valid) / len(valid), 3)
        else:
            score = None
            confidence = 0.35
        results.append({
            "skill": skill,
            "baseline_score": score,
            "confidence": confidence,
            "direct_evidence": bool(valid),
            "items_attempted": sum(item["items_attempted"] for item in evidence),
            "items_available": sum(item["items_available"] for item in evidence),
        })
    return results


def _save_baseline(user_id: str, result: Mapping[str, Any], columns: set[str]) -> None:
    from personalized_practice.models import LearnerSkillBaseline

    table = connection.ops.quote_name(LearnerSkillBaseline._meta.db_table)
    fields = ["user_id", "skill", "baseline_score", "confidence", "direct_evidence", "trend", "error_counts"]
    values = ["%s", "%s", "%s", "%s", "%s", "%s", "(%s)::jsonb"]
    params: list[Any] = [
        user_id,
        result["skill"],
        result["baseline_score"],
        result["confidence"],
        result["direct_evidence"],
        "unknown",
        json.dumps({}),
    ]
    if "metrics" in columns:
        fields.append("metrics")
        values.append("(%s)::jsonb")
        params.append(json.dumps({}))
    fields.append("updated_at")
    values.append("CURRENT_TIMESTAMP")
    quoted_fields = [connection.ops.quote_name(field) for field in fields]
    baseline_score = connection.ops.quote_name("baseline_score")
    confidence = connection.ops.quote_name("confidence")
    direct_evidence = connection.ops.quote_name("direct_evidence")
    updated_at = connection.ops.quote_name("updated_at")
    assignments = ", ".join((
        f"{baseline_score} = COALESCE(EXCLUDED.{baseline_score}, {table}.{baseline_score})",
        f"{confidence} = CASE WHEN EXCLUDED.{baseline_score} IS NULL "
        f"THEN {table}.{confidence} ELSE EXCLUDED.{confidence} END",
        f"{direct_evidence} = {table}.{direct_evidence} OR EXCLUDED.{direct_evidence}",
        f"{updated_at} = CURRENT_TIMESTAMP",
    ))
    sql = (
        f"INSERT INTO {table} ({', '.join(quoted_fields)}) "
        f"VALUES ({', '.join(values)}) "
        f"ON CONFLICT ({connection.ops.quote_name('user_id')}, {connection.ops.quote_name('skill')}) "
        f"DO UPDATE SET {assignments}"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, params)


@transaction.atomic
def save_assessment_results(user, results: list[dict[str, Any]]) -> None:
    from personalized_practice.models import LearnerSkillBaseline
    from user.models import Profile, Skill

    profile = Profile.objects.select_related("skills").get(user_id=user.pk)
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor, LearnerSkillBaseline._meta.db_table
        )
    columns = {column.name for column in description}
    skill_updates = {}
    for result in results:
        _save_baseline(str(user.pk), result, columns)
        field = SKILL_FIELD_MAP.get(result["skill"])
        if field and result["baseline_score"] is not None:
            skill_updates[field] = result["baseline_score"]
    if profile.skills_id and skill_updates:
        Skill.objects.filter(pk=profile.skills_id).update(**skill_updates)
    type(user).objects.filter(pk=user.pk).update(assessment_completed=True)


def get_assessment_results(
    age_group: str,
    submission: Mapping[str, Any],
    verified_speech_scores: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    try:
        return score_assessment(age_group, submission, verified_speech_scores)
    except PracticeDataError as exc:
        raise AssessmentSubmissionError(str(exc)) from exc
    except SpeechScoringError as exc:
        raise AssessmentSubmissionError(str(exc)) from exc