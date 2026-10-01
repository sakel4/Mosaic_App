import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from personalized_practice.domain import PracticeDataError


BANK_DIRECTORY = Path(__file__).resolve().parents[1] / "Exercises-AI"
BANK_FILES = {
    "under_12": "under_12.json",
    "12_15": "12-15.json",
    "16_18": "16-18.json",
    "19_plus": "19_plus.json",
}
PRIVATE_FIELDS = {
    "answer_key",
    "answer_keys",
    "answers",
    "correct_answer",
    "correct_option_id",
    "private_scoring",
    "scoring",
}
SKILL_ALIASES = {
    "decoding": "decoding_and_word_recognition",
    "word_recognition": "decoding_and_word_recognition",
    "reading_comprehension": "comprehension",
    "orthographic_knowledge": "letter_sound",
}


@lru_cache(maxsize=4)
def load_age_bank(age_group: str) -> dict[str, Any]:
    try:
        file_name = BANK_FILES[age_group]
    except KeyError as exc:
        raise PracticeDataError("Unsupported age group.") from exc
    path = BANK_DIRECTORY / file_name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PracticeDataError(f"Could not load exercise bank for {age_group}.") from exc
    if data.get("age_group") != age_group or not isinstance(data.get("exercises"), list):
        raise PracticeDataError(f"Exercise bank metadata is invalid for {age_group}.")
    return data


def public_content(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: public_content(item)
            for key, item in value.items()
            if str(key).casefold() not in PRIVATE_FIELDS
        }
    if isinstance(value, list):
        return [public_content(item) for item in value]
    return value


def public_seed(exercise: Mapping[str, Any]) -> dict[str, Any]:
    return public_content(
        {
            "id": exercise.get("id"),
            "kind": exercise.get("kind"),
            "skill": exercise.get("skill"),
            "difficulty": exercise.get("difficulty"),
            "response_type": exercise.get("response_type"),
            "instruction": exercise.get("instruction"),
            "prompt": exercise.get("prompt"),
            "content_data": exercise.get("content_data", {}),
        }
    )


def supported_skills(age_group: str) -> set[str]:
    bank_skills = {str(item.get("skill")) for item in load_age_bank(age_group)["exercises"]}
    return bank_skills | {
        alias for alias, bank_skill in SKILL_ALIASES.items() if bank_skill in bank_skills
    }


def select_seed(age_group: str, skill: str, recent_source_ids: set[str]) -> dict[str, Any]:
    bank = load_age_bank(age_group)
    target_bank_skill = SKILL_ALIASES.get(skill, skill)
    candidates = [
        exercise
        for exercise in bank["exercises"]
        if exercise.get("skill") == target_bank_skill
    ]
    if not candidates:
        raise PracticeDataError(f"No age-appropriate bank seed exists for skill '{skill}'.")
    candidates.sort(key=lambda item: (int(item.get("position", 0)), str(item.get("id", ""))))
    fresh = [item for item in candidates if str(item.get("id")) not in recent_source_ids]
    return public_seed((fresh or candidates)[0])
