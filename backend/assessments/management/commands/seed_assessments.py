import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from assessments.choices import Kind, ResponseType, Skill
from assessments.models import Assessment, AssessmentExcercise
from user.choices import AgeGroup

SOURCE_DIR = Path(settings.BASE_DIR) / "Exercises-AI"

# JSON values that are not in assessments.choices, mapped to the closest valid choice.
SKILL_MAP = {
    "letter_sound": Skill.LETTER_SOUND_ASSOCIATION.value,
    "decoding_and_word_recognition": Skill.DECODING.value,
    "visual_retrieval_speed": Skill.NAMING_SPEED.value,
}
RESPONSE_TYPE_MAP = {
    "typed_text": ResponseType.SPELLING.value,
}


class Command(BaseCommand):
    help = "Seed one Assessment (with its exercises) per age group from Exercises-AI/structure_*.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace an existing assessment of the same age_group and assessment_type.",
        )
        parser.add_argument(
            "--dir",
            default=str(SOURCE_DIR),
            help="Directory containing the structure_*.json files.",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["dir"])
        files = sorted(source_dir.glob("structure_*.json"))
        if not files:
            raise CommandError(f"No structure_*.json files found in {source_dir}")

        # Validate and parse everything first so a bad file never leaves a partial seed.
        parsed = [(f, self._load(f)) for f in files]

        found = {data["age_group"] for _, data in parsed}
        missing = set(AgeGroup.values) - found
        if missing:
            self.stdout.write(self.style.WARNING(f"No file found for age groups: {', '.join(sorted(missing))}"))

        with transaction.atomic():
            for path, data in parsed:
                self._seed(path, data, options["replace"])

    def _load(self, path):
        try:
            with path.open(encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as exc:
            raise CommandError(f"{path.name}: invalid JSON ({exc})")

        data = payload.get("assessment")
        if not isinstance(data, dict):
            raise CommandError(f"{path.name}: missing 'assessment' object")
        if data.get("age_group") not in AgeGroup.values:
            raise CommandError(f"{path.name}: invalid age_group {data.get('age_group')!r}")
        if not data.get("excercises"):
            raise CommandError(f"{path.name}: no 'excercises' defined")
        return data

    def _seed(self, path, data, replace):
        age_group = data["age_group"]
        assessment_type = data.get("assessment_type", "")

        language = data.get("language", "en")

        existing = Assessment.objects.filter(
            age_group=age_group, assessment_type=assessment_type, language=language
        )
        if existing.exists():
            if not replace:
                self.stdout.write(
                    self.style.WARNING(f"[{age_group}/{language}] already exists, skipped (use --replace).")
                )
                return
            existing.delete()

        assessment = Assessment.objects.create(
            age_group=age_group,
            language=language,
            estimated_duration_seconds=data.get("estimated_duration_seconds"),
            estimated_voice_duration_seconds=data.get("estimated_voice_duration_seconds"),
            assessment_type=assessment_type,
        )

        # created_at is auto_now_add, so it can only be overridden with an update.
        created_at = parse_datetime(data["created_at"]) if data.get("created_at") else None
        if created_at:
            Assessment.objects.filter(pk=assessment.pk).update(created_at=created_at)

        exercises = []
        for ex in data["excercises"]:
            kind = ex.get("kind", "")
            skill = SKILL_MAP.get(ex.get("skill"), ex.get("skill", ""))
            response_type = RESPONSE_TYPE_MAP.get(ex.get("response_type"), ex.get("response_type", ""))

            for label, value, valid in (
                ("kind", kind, Kind.values),
                ("skill", skill, Skill.values),
                ("response_type", response_type, ResponseType.values),
            ):
                if value not in valid:
                    raise CommandError(f"{path.name}: position {ex.get('position')} has invalid {label} {value!r}")

            exercises.append(
                AssessmentExcercise(
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
            )

        AssessmentExcercise.objects.bulk_create(exercises)
        self.stdout.write(
            self.style.SUCCESS(f"[{age_group}/{language}] created assessment {assessment.id} with {len(exercises)} exercises.")
        )
