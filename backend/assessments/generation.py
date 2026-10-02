import json
import logging
from collections.abc import Mapping
from decimal import Decimal

from django.db.models import Prefetch

from bedrock import BedrockError, BedrockNotConfigured, converse_json
from user.choices import AgeGroup

from .choices import AssessmentType, Kind, ResponseType, Skill
from .models import Assessment, AssessmentExcercise, SkillHistory
from .utils import InvalidAssessmentError, insert_assessment

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 4000
EXERCISE_MAX_OUTPUT_TOKENS = 8000

# The model occasionally returns the wrong count or an invalid enum value.
MAX_ATTEMPTS = 3
EXERCISE_COUNT = 7
EXERCISE_RATIO = (("weakest", 0.60), ("improving", 0.25), ("maintenance", 0.15))
# Number of recent skill snapshots used to decide which skill is improving.
TREND_SNAPSHOTS = 3
# Reference-bank skills that cover learner skills under other names.
REFERENCE_TO_LEARNER_SKILLS = {
    "letter_sound": ("letter_sound_association",),
    "decoding_and_word_recognition": ("decoding", "word_recognition"),
    "visual_retrieval_speed": ("naming_speed",),
}


class AssessmentGenerationError(Exception):
    pass


def _reference_assessments() -> list[dict]:
    """The newest default ASSESSMENT per age group, in structure_*.json shape."""
    newest = {}
    queryset = (
        Assessment.objects.filter(assessment_type=AssessmentType.ASSESSMENT)
        .prefetch_related(
            Prefetch("excercises", queryset=AssessmentExcercise.objects.order_by("position"))
        )
        .order_by("created_at")
    )
    for assessment in queryset:
        newest[assessment.age_group] = assessment

    references = []
    for age_group in AgeGroup.values:
        assessment = newest.get(age_group)
        if assessment is None:
            continue
        references.append(
            {
                "age_group": assessment.age_group,
                "language": assessment.language,
                "assessment_type": assessment.assessment_type,
                "excercises": [
                    {
                        "position": ex.position,
                        "kind": ex.kind,
                        "skill": ex.skill,
                        "difficulty": ex.difficulty_level,
                        "response_type": ex.response_type,
                        "instruction": ex.instruction,
                        "content_data": ex.content_data,
                        "answers": ex.answers,
                    }
                    for ex in assessment.excercises.all()
                ],
            }
        )
    if not references:
        raise AssessmentGenerationError("No default assessments are loaded to use as a reference.")
    return references


_DEFAULT_TARGETING = """The user message gives the learner's age_group, the requested assessment_type and the learner's current skill scores (0-100, listed lowest first).
Target the learner's weakest skills: build the exercise around the lowest-scoring skill that has a matching exercise kind in the reference for that age_group, and pick a difficulty slightly above that score level."""

_EXERCISE_TARGETING = """The user message gives the learner's age_group, language, current skill scores (0-100) and an exercise_plan.
exercise_plan has one entry per exercise with a position, a skill and a role. Create exactly one exercise per entry, in that order, measuring exactly that skill; choose a kind from the reference that fits the skill and the age_group.
The role sets the difficulty relative to the learner's score for that skill: "weakest" slightly above it, "improving" about the same, "maintenance" slightly below it so a strong skill stays fresh.
Vary the kinds, topics and content across the exercises."""


def build_system_prompt(references: list[dict], assessment_type: str = "") -> str:
    references = json.dumps(references, ensure_ascii=False, separators=(",", ":"))
    targeting = _EXERCISE_TARGETING if assessment_type == AssessmentType.EXCERCISE else _DEFAULT_TARGETING
    return f"""You create reading and literacy practice content for the Mosaic learning app.
This is educational practice, never a diagnosis or clinical assessment.

Below are the default assessments, one per age group, as JSON. They are the authoritative reference for the JSON structure, exercise kinds, skills, response types, content_data shape, answers format, and the difficulty, vocabulary and language complexity that suit each age group.
Never copy their wording, passages, items, options or answers. Create new original content.

DEFAULT_ASSESSMENTS:
{references}

{targeting}

Rules:
- Return only one JSON object, starting with {{ and ending with }}. No markdown fences or commentary.
- Shape: {{"assessment": {{"age_group", "language", "assessment_type", "excercises": [{{"position", "kind", "skill", "difficulty", "response_type", "instruction", "content_data", "answers"}}]}}}}
- The key is spelled "excercises" and must be used exactly like that.
- Use the age_group, language and assessment_type given by the user.
- positions start at 1.
- kind must be one of: {", ".join(Kind.values)}.
- skill must be one of: {", ".join(Skill.values)}.
- response_type must be one of: {", ".join(ResponseType.values)}, and should match the reference exercise of the same kind (for example spelling uses typed_text).
- content_data and answers must follow the same shape as the reference exercise of the same kind, with every item id in content_data present in answers.
- answers must be correct and unambiguous."""


def _scores(skills: Mapping[str, Decimal | float | None]) -> dict[str, float]:
    scored = {name: float(value) for name, value in skills.items() if value is not None}
    return dict(sorted(scored.items(), key=lambda item: item[1]))


def _supported_skills(references: list[dict], age_group: str) -> set[str]:
    """Learner skills that the reference assessment of this age group has exercises for."""
    supported = set()
    for reference in references:
        if reference.get("age_group") != age_group:
            continue
        for exercise in reference.get("excercises", []):
            skill = exercise.get("skill")
            supported.update(REFERENCE_TO_LEARNER_SKILLS.get(skill, (skill,)))
    return supported


def _improvement(user, scores: Mapping[str, float]) -> dict[str, float]:
    """Score change per skill across the user's most recent evaluation snapshots."""
    if user is None:
        return {}
    snapshots = list(
        SkillHistory.objects.filter(assessment_evaluation__user_id=user).order_by("-created_at")[:TREND_SNAPSHOTS]
    )
    if len(snapshots) < 2:
        return {}
    latest, oldest = snapshots[0], snapshots[-1]
    change = {}
    for name in scores:
        new, old = getattr(latest, name, None), getattr(oldest, name, None)
        if new is not None and old is not None:
            change[name] = float(new) - float(old)
    return change


def _split_counts(total: int) -> list[int]:
    """Split total by EXERCISE_RATIO using the largest-remainder method."""
    raw = [total * share for _, share in EXERCISE_RATIO]
    counts = [int(value) for value in raw]
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True)
    for index in by_remainder[: total - sum(counts)]:
        counts[index] += 1
    return counts


def build_exercise_plan(
    scores: Mapping[str, float], improvement: Mapping[str, float], total: int = EXERCISE_COUNT
) -> list[dict]:
    """One entry per exercise: the weakest skill, the most improving skill, and a strong skill to maintain."""
    ranked = sorted(scores, key=scores.__getitem__)
    weakest = ranked[0]
    rest = ranked[1:]
    maintenance = rest[-1] if rest else weakest
    candidates = [skill for skill in rest if skill != maintenance]
    gaining = [skill for skill in candidates if improvement.get(skill, 0) > 0]
    if gaining:
        improving = max(gaining, key=lambda skill: improvement[skill])
    else:
        improving = candidates[0] if candidates else maintenance

    chosen = {"weakest": weakest, "improving": improving, "maintenance": maintenance}
    plan = []
    for (role, _), count in zip(EXERCISE_RATIO, _split_counts(total)):
        plan.extend({"skill": chosen[role], "role": role} for _ in range(count))
    return [{"position": position, **entry} for position, entry in enumerate(plan, start=1)]


def generate_assessment(
    *,
    assessment_type: str,
    age_group: str,
    skills: Mapping[str, Decimal | float | None],
    user=None,
    language: str = "en",
) -> Assessment:
    scores = _scores(skills)
    if not scores:
        raise AssessmentGenerationError("The learner has no skill scores yet.")

    references = _reference_assessments()
    plan = None
    request = {
        "age_group": age_group,
        "language": language,
        "assessment_type": assessment_type,
        "number_of_exercises": 1,
        "current_skill_scores": scores,
    }
    max_tokens = MAX_OUTPUT_TOKENS
    if assessment_type == AssessmentType.EXCERCISE:
        supported = _supported_skills(references, age_group)
        plannable = {name: value for name, value in scores.items() if name in supported} or scores
        plan = build_exercise_plan(plannable, _improvement(user, plannable))
        request.update(number_of_exercises=len(plan), exercise_plan=plan)
        max_tokens = EXERCISE_MAX_OUTPUT_TOKENS

    system = build_system_prompt(references, assessment_type)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _generate_once(
                request=request,
                system=system,
                max_tokens=max_tokens,
                plan=plan,
                age_group=age_group,
                language=language,
                assessment_type=assessment_type,
                user=user,
            )
        except BedrockNotConfigured:
            raise
        except (BedrockError, AssessmentGenerationError):
            if attempt == MAX_ATTEMPTS:
                raise
            logger.warning("Assessment generation attempt %s failed; retrying", attempt, exc_info=True)


def strip_first_letter_of_options(exercise: dict) -> None:
    """Drop the first letter of each option text, e.g. "triple" becomes "riple"."""
    content = exercise.get("content_data")
    items = content.get("items") if isinstance(content, dict) else None
    for item in items if isinstance(items, list) else []:
        options = item.get("options") if isinstance(item, dict) else None
        for option in options if isinstance(options, list) else []:
            text = option.get("text") if isinstance(option, dict) else None
            # Sound-notation options like "/s/ /p/" are not words.
            if isinstance(text, str) and len(text) > 1 and not text.startswith("/"):
                option["text"] = text[1:]


def _generate_once(
    *, request, system, max_tokens, plan, age_group, language, assessment_type, user
) -> Assessment:
    generated = converse_json(
        json.dumps(request, ensure_ascii=False),
        system=system,
        max_tokens=max_tokens,
    )

    data = generated.get("assessment", generated)
    if not isinstance(data, dict):
        raise AssessmentGenerationError("Generated assessment has an invalid shape.")
    data.update(age_group=age_group, language=language, assessment_type=assessment_type)
    # The model sometimes "corrects" the schema's misspelled key.
    if not data.get("excercises") and data.get("exercises"):
        data["excercises"] = data.pop("exercises")

    if plan:
        exercises = data.get("excercises")
        if (
            not isinstance(exercises, list)
            or len(exercises) != len(plan)
            or not all(isinstance(item, dict) for item in exercises)
        ):
            raise AssessmentGenerationError(f"Expected {len(plan)} generated exercises.")
        for exercise, entry in zip(exercises, plan):
            produced = exercise.get("skill")
            if entry["skill"] not in REFERENCE_TO_LEARNER_SKILLS.get(produced, (produced,)):
                raise AssessmentGenerationError(
                    f"Exercise {entry['position']} measures {produced!r}, expected {entry['skill']!r}."
                )
            exercise["position"] = entry["position"]
            exercise["skill"] = entry["skill"]

    if assessment_type == AssessmentType.EXCERCISE:
        for exercise in data.get("excercises") or []:
            if (
                isinstance(exercise, dict)
                and exercise.get("kind") == Kind.PHONEME_MANIPULATION
                and exercise.get("skill") == Skill.PHONOLOGICAL_AWARENESS
            ):
                strip_first_letter_of_options(exercise)

    try:
        return insert_assessment(data, user=user)
    except InvalidAssessmentError as exc:
        raise AssessmentGenerationError(str(exc)) from exc
