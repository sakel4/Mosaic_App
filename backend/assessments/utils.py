from collections.abc import Mapping
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_datetime

from user.choices import AgeGroup

from .choices import Kind, ResponseType, Skill
from .models import Assessment, AssessmentExcercise

# Values that are not in assessments.choices, mapped to the closest valid choice.
SKILL_MAP = {
    "letter_sound": Skill.LETTER_SOUND_ASSOCIATION.value,
    "decoding_and_word_recognition": Skill.DECODING.value,
    "visual_retrieval_speed": Skill.NAMING_SPEED.value,
}


class InvalidAssessmentError(ValueError):
    pass


def insert_assessment(data: Mapping[str, Any], user=None) -> Assessment:
    """Insert an Assessment and its exercises from a structure_*.json-shaped dict.

    Accepts either {"assessment": {...}} or the inner assessment object.
    Nothing is saved if any part of the data is invalid.
    """
    data = data.get("assessment", data)
    if not isinstance(data, Mapping):
        raise InvalidAssessmentError("Missing 'assessment' object.")
    if data.get("age_group") not in AgeGroup.values:
        raise InvalidAssessmentError(f"Invalid age_group {data.get('age_group')!r}.")
    if not data.get("excercises"):
        raise InvalidAssessmentError("No 'excercises' defined.")

    assessment = Assessment(
        age_group=data["age_group"],
        language=data.get("language", "en"),
        estimated_duration_seconds=data.get("estimated_duration_seconds"),
        estimated_voice_duration_seconds=data.get("estimated_voice_duration_seconds"),
        assessment_type=data.get("assessment_type", ""),
        user=user,
    )
    exercises = [_build_exercise(assessment, ex) for ex in data["excercises"]]

    with transaction.atomic():
        assessment.save(force_insert=True)

        # created_at is auto_now_add, so it can only be overridden with an update.
        created_at = parse_datetime(data["created_at"]) if data.get("created_at") else None
        if created_at:
            Assessment.objects.filter(pk=assessment.pk).update(created_at=created_at)

        AssessmentExcercise.objects.bulk_create(exercises)

    return assessment


def _build_exercise(assessment: Assessment, ex: Mapping[str, Any]) -> AssessmentExcercise:
    if ex.get("position") is None:
        raise InvalidAssessmentError("Every exercise needs a 'position'.")

    kind = ex.get("kind", "")
    skill = SKILL_MAP.get(ex.get("skill"), ex.get("skill", ""))
    response_type = ex.get("response_type", "")

    for label, value, valid in (
        ("kind", kind, Kind.values),
        ("skill", skill, Skill.values),
        ("response_type", response_type, ResponseType.values),
    ):
        if value not in valid:
            raise InvalidAssessmentError(f"Position {ex['position']} has invalid {label} {value!r}.")

    return AssessmentExcercise(
        assessment=assessment,
        position=ex["position"],
        kind=kind,
        skill=skill,
        difficulty_level=ex.get("difficulty"),
        response_type=response_type,
        instruction=ex.get("instruction", ""),
        content_data=ex.get("content_data"),
        answers=ex.get("answers"),
        confidence=ex.get("confidence"),
    )
