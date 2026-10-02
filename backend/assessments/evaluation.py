import json
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from django.db import transaction

from bedrock import converse_json
from user.models import Skill as UserSkill

from .choices import AssessmentType
from .models import Assessment, AssessmentEvaluation, SkillHistory

SKILL_FIELDS = [f.name for f in UserSkill._meta.concrete_fields if f.name != "id"]
# Largest change a single non-baseline evaluation may apply to one skill.
MAX_SKILL_STEP = 10
MAX_ERROR_TYPES = 20
MAX_OUTPUT_TOKENS = 1500


class EvaluationError(Exception):
    pass


def _current_skills(skills: UserSkill | None) -> dict[str, float | None]:
    return {
        field: (float(value) if (value := getattr(skills, field, None)) is not None else None)
        for field in SKILL_FIELDS
    }


def _assessment_payload(assessment: Assessment) -> dict[str, Any]:
    return {
        "id": str(assessment.pk),
        "age_group": assessment.age_group,
        "language": assessment.language,
        "assessment_type": assessment.assessment_type,
        "exercises": [
            {
                "id": str(ex.pk),
                "exercise_id": ex.exercise_id,
                "position": ex.position,
                "kind": ex.kind,
                "skill": ex.skill,
                "difficulty": ex.difficulty_level,
                "response_type": ex.response_type,
                "instruction": ex.instruction,
                "content_data": ex.content_data,
                "correct_answers": ex.answers,
                "confidence": float(ex.confidence) if ex.confidence is not None else None,
            }
            for ex in assessment.excercises.order_by("position")
        ],
    }


def _system_prompt(baseline: bool) -> str:
    skills = ", ".join(SKILL_FIELDS)
    common = f"""You evaluate a learner's answers to a reading and literacy exercise set for the Mosaic app.
This is educational practice, never a diagnosis or clinical assessment.

The user message is JSON with the full assessment (exercises, content, correct_answers, and per-exercise confidence from 0 to 100) and the learner's answers, keyed by exercise id or item id.
Compare the learner's answers with correct_answers; for spoken or typed answers judge them against the instruction and content.
Exercise confidence says how reliably that exercise measures its skill: weight low-confidence exercises less.

Skill names you may return: {skills}.
Map exercise skills to these names: letter_sound -> letter_sound_association; decoding_and_word_recognition -> both decoding and word_recognition.
Only return skills that the exercises actually measure. Scores are numbers from 0 to 100.
Also return error_types: a short list of snake_case labels for the mistake patterns you saw (an empty list if none).

Return only one JSON object, starting with {{ and ending with }}, without markdown fences or commentary:
{{"skills": {{"<skill>": <number>}}, "error_types": ["<label>"]}}"""
    if baseline:
        return common + """

This is a baseline assessment. Score each measured skill on its own from this performance, with no prior values."""
    return common + f"""

current_skills holds the learner's present scores (null means no score yet).
Return the updated score for each measured skill, moving it from its current value according to this performance:
- Change gradually. A single result must never move a skill by more than {MAX_SKILL_STEP} points; typical changes are a few points.
- Good performance raises the score, poor performance lowers it, and performance in line with the current score changes it very little.
- If a current score is null, score the skill directly from this performance."""


def _parse_scores(raw: Any) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise EvaluationError("Evaluation response has no skill scores.")
    scores = {
        name: min(100.0, max(0.0, float(value)))
        for name, value in raw.items()
        if name in SKILL_FIELDS and isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    if not scores:
        raise EvaluationError("Evaluation response has no valid skill scores.")
    return scores


def _limit_change(previous: float | None, new: float) -> float:
    if previous is None:
        return new
    return min(max(new, previous - MAX_SKILL_STEP), previous + MAX_SKILL_STEP)


def _error_types(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str) and item][:MAX_ERROR_TYPES]


def evaluate_assessment(
    *,
    assessment: Assessment,
    answers: Mapping[str, Any],
    user,
    profile,
    is_initial: bool,
) -> AssessmentEvaluation:
    baseline = assessment.assessment_type == AssessmentType.ASSESSMENT
    current = _current_skills(profile.skills)

    request = {
        "is_initial": is_initial,
        "assessment": _assessment_payload(assessment),
        "learner_answers": answers,
    }
    if not baseline:
        request["current_skills"] = current

    result = converse_json(
        json.dumps(request, ensure_ascii=False, default=str),
        system=_system_prompt(baseline),
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0.2,
    )
    scores = _parse_scores(result.get("skills"))
    if not baseline:
        scores = {name: _limit_change(current[name], value) for name, value in scores.items()}

    with transaction.atomic():
        skills = profile.skills or UserSkill.objects.create()
        for name, value in scores.items():
            setattr(skills, name, Decimal(str(round(value, 2))))
        skills.save()
        if profile.skills_id is None:
            profile.skills = skills
            profile.save(update_fields=["skills"])

        history = SkillHistory.objects.create(**{f: getattr(skills, f) for f in SKILL_FIELDS})
        return AssessmentEvaluation.objects.create(
            assessment=assessment,
            user_id=user,
            answers=answers,
            error_types=_error_types(result.get("error_types")),
            updated_skills=history,
        )
