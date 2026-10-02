import json
import logging
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from django.db import transaction

from bedrock import BedrockError, BedrockNotConfigured, converse_json

from .models import RealLifeSet, RealLifeSetExercise

logger = logging.getLogger(__name__)

BANK_PATH = Path(__file__).resolve().parents[1] / "Exercises-AI" / "real_life_exercises.json"
# The bank files the 19+ group under "18_plus".
BANK_AGE_GROUP_KEYS = {"19_plus": "18_plus"}
EXERCISE_COUNT = 3
MAX_OUTPUT_TOKENS = 3000
# The model occasionally returns malformed or inconsistent exercises.
MAX_ATTEMPTS = 3
TITLE_LIMIT = 255
CONTEXT_LIMIT = 255


class RealLifeGenerationError(Exception):
    pass


def _load_bank() -> dict[str, Any]:
    try:
        return json.loads(BANK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RealLifeGenerationError("Could not load the real-life exercise bank.") from exc


def build_system_prompt(bank: Mapping[str, Any], age_group: str) -> str:
    bank_key = BANK_AGE_GROUP_KEYS.get(age_group, age_group)
    reference = json.dumps(bank, ensure_ascii=False, separators=(",", ":"))
    return f"""You create everyday-life reading practice for the Mosaic learning app. Learners may have dyslexia, so the text must be clear and short.
This is educational practice, never a diagnosis or medical advice.

REAL_LIFE_EXERCISES below is the reference bank, as JSON. It holds a category and, per age group, example exercises that show the structure, topics, reading level and difficulty. The learner's age group matches the "{bank_key}" examples.
Never copy their wording, numbers or answers. Create new original exercises.

REAL_LIFE_EXERCISES:
{reference}

The user message gives the learner's age_group, language, the number of exercises, and details about the learner (interests, learning goal, and skill scores from 0 to 100 where lower means weaker).
Choose one category of everyday life that suits the age range and the learner, as a short name like the bank's "Everyday Life & Dyslexia" (for example "Money & Shopping"), and write exercises about different realistic situations in that category.
Adapt the situations to the learner's interests where it feels natural, and keep the reading load suited to their weaker skills.

Rules:
- Return only one JSON object, starting with {{ and ending with }}. No markdown fences or commentary.
- Shape: {{"category": "...", "exercises": [{{"title", "context", "information", "question", "options", "correct_answer"}}]}}
- Write exactly the requested number of exercises.
- title looks like "Topic — focus". context is a short uppercase label for the situation. Both stay under 100 characters.
- information is an array of short lines the learner reads (prices, times, signs, steps, messages).
- options is an array of 3 or 4 different short strings.
- correct_answer is an array holding the exact text of the correct option; use exactly one unless the question clearly asks for several.
- The answer must follow from the information alone and be unambiguous; check it twice if it needs arithmetic or a time calculation.
- Write in the learner's language, in short plain sentences without idioms."""


def _text(value: Any, field: str, limit: int | None = None) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise RealLifeGenerationError(f"{field} must be a non-empty string.")
    value = value.strip()
    if limit is not None and len(value) > limit:
        raise RealLifeGenerationError(f"{field} is longer than {limit} characters.")
    return value


def _text_list(value: Any, field: str) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        raise RealLifeGenerationError(f"{field} must be a non-empty list.")
    return [_text(item, field) for item in value]


def _parse_exercise(raw: Any, position: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RealLifeGenerationError(f"Exercise {position} has an invalid shape.")

    options = _text_list(raw.get("options"), "options")
    canonical = {option.casefold(): option for option in options}
    if len(options) < 2 or len(canonical) != len(options):
        raise RealLifeGenerationError(f"Exercise {position} needs at least two different options.")

    answers = []
    for answer in _text_list(raw.get("correct_answer"), "correct_answer"):
        option = canonical.get(answer.casefold())
        if option is None:
            raise RealLifeGenerationError(f"Exercise {position} has an answer that is not an option.")
        if option not in answers:
            answers.append(option)

    return {
        "title": _text(raw.get("title"), "title", TITLE_LIMIT),
        "context": _text(raw.get("context"), "context", CONTEXT_LIMIT),
        "information": _text_list(raw.get("information"), "information"),
        "question": _text(raw.get("question"), "question"),
        "options": options,
        "correct_answer": answers,
    }


def _parse_set(data: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    category = _text(data.get("category"), "category")
    raw_exercises = data.get("exercises")
    if not isinstance(raw_exercises, list) or len(raw_exercises) != EXERCISE_COUNT:
        raise RealLifeGenerationError(f"Expected {EXERCISE_COUNT} generated exercises.")
    return category, [_parse_exercise(raw, n) for n, raw in enumerate(raw_exercises, start=1)]


def _save(age_group: str, category: str, exercises: list[dict[str, Any]]) -> RealLifeSet:
    set_id = uuid.uuid4().hex
    with transaction.atomic():
        real_life_set = RealLifeSet.objects.create(id=set_id, age_group=age_group, category=category)
        RealLifeSetExercise.objects.bulk_create(
            RealLifeSetExercise(id=f"{set_id}_{n:02d}", real_life_set=real_life_set, **exercise)
            for n, exercise in enumerate(exercises, start=1)
        )
    return real_life_set


def generate_real_life_set(
    *,
    age_group: str,
    language: str = "en",
    interests: Iterable[str] = (),
    learning_goal: str = "",
    skills: Mapping[str, Any] | None = None,
) -> RealLifeSet:
    system = build_system_prompt(_load_bank(), age_group)
    request = {
        "age_group": age_group,
        "language": language,
        "number_of_exercises": EXERCISE_COUNT,
        "learner": {
            "interests": list(interests),
            "learning_goal": learning_goal,
            "skill_scores": {
                name: float(value) for name, value in (skills or {}).items() if value is not None
            },
        },
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            generated = converse_json(
                json.dumps(request, ensure_ascii=False),
                system=system,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
            category, exercises = _parse_set(generated)
            return _save(age_group, category, exercises)
        except BedrockNotConfigured:
            raise
        except (BedrockError, RealLifeGenerationError):
            if attempt == MAX_ATTEMPTS:
                raise
            logger.warning("Real-life set generation attempt %s failed; retrying", attempt, exc_info=True)
