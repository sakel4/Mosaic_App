import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assessments.choices import AssessmentType, Kind, ResponseType, Skill
from assessments.models import Assessment, AssessmentExcercise


BANK_DIRECTORY = Path(__file__).resolve().parents[3] / "Exercises-AI"
BANK_FILES = {
    "under_12": "structure_under_12.json",
    "12_15": "structure_12-15.json",
    "16_18": "structure_16-18.json",
    "19_plus": "structure_19_plus.json",
}


class Command(BaseCommand):
    help = "Load assessments from exercise bank structure files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--age-groups",
            type=str,
            default="",
            help="Comma-separated list of age groups to load (default: all)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing assessments before loading",
        )

    def handle(self, *args, **options):
        age_groups_arg = options.get("age_groups", "").strip()
        reset_flag = options.get("reset", False)
        
        if age_groups_arg:
            age_groups = [ag.strip() for ag in age_groups_arg.split(",")]
        else:
            age_groups = list(BANK_FILES.keys())

        # Validate age groups
        valid_groups = set(BANK_FILES.keys())
        invalid = set(age_groups) - valid_groups
        if invalid:
            raise CommandError(f"Invalid age groups: {', '.join(invalid)}")

        # Reset if requested
        if reset_flag:
            count = Assessment.objects.filter(
                assessment_type=AssessmentType.ASSESSMENT,
                age_group__in=age_groups,
            ).delete()[0]
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing assessments"))

        # Load assessments
        created_count = 0
        for age_group in age_groups:
            try:
                created = self._load_age_group(age_group)
                created_count += created
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Loaded {created} exercises for {age_group}")
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to load {age_group}: {str(exc)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Successfully loaded {created_count} total exercises")
        )

    def _load_age_group(self, age_group: str) -> int:
        """Load assessment for a single age group. Returns number of exercises created."""
        file_name = BANK_FILES[age_group]
        path = BANK_DIRECTORY / file_name

        if not path.exists():
            raise CommandError(f"Bank file not found: {path}")

        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read or parse {file_name}: {str(exc)}")

        # Extract assessment data (handle nested "assessment" structure)
        if "assessment" in raw_data:
            assessment_data = raw_data["assessment"]
        else:
            assessment_data = raw_data

        # Validate required fields
        self._validate_assessment_data(assessment_data, age_group)

        # Get or create Assessment
        assessment_version = assessment_data.get(
            "assessment_version", f"onoma_en_{age_group}_limited_voice_v2"
        )
        assessment, created = Assessment.objects.get_or_create(
            age_group=age_group,
            assessment_type=AssessmentType.ASSESSMENT,
            defaults={
                "language": assessment_data.get("language", "en"),
                "estimated_duration_seconds": assessment_data.get("estimated_duration_seconds"),
                "estimated_voice_duration_seconds": assessment_data.get(
                    "estimated_voice_duration_seconds"
                ),
            },
        )

        # Handle both "exercises" and misspelled "excercises"
        exercises = assessment_data.get("exercises") or assessment_data.get("excercises", [])

        if not isinstance(exercises, list) or not exercises:
            raise CommandError(f"No exercises found in {BANK_FILES[age_group]}")

        # Create or update AssessmentExcercise records
        exercise_count = 0
        for exercise_data in exercises:
            try:
                self._create_exercise(assessment, exercise_data, age_group)
                exercise_count += 1
            except Exception as exc:
                pos = exercise_data.get("position", "?")
                raise CommandError(
                    f"Failed to create exercise at position {pos}: {str(exc)}"
                )

        return exercise_count

    def _validate_assessment_data(self, assessment_data: dict, age_group: str) -> None:
        """Validate that assessment data has required structure."""
        if assessment_data.get("age_group") != age_group:
            raise CommandError(
                f"Assessment age_group mismatch: expected {age_group}, "
                f"got {assessment_data.get('age_group')}"
            )

        exercises = assessment_data.get("exercises") or assessment_data.get("excercises")
        if not isinstance(exercises, list):
            raise CommandError("Assessment must contain 'exercises' array")

    def _create_exercise(self, assessment: Assessment, exercise_data: dict, age_group: str) -> None:
        """Create or update an AssessmentExcercise record."""
        # Extract and validate required fields
        position = exercise_data.get("position")
        kind = exercise_data.get("kind")
        skill = exercise_data.get("skill")
        difficulty = exercise_data.get("difficulty")
        response_type = exercise_data.get("response_type")
        instruction = exercise_data.get("instruction", "")
        content_data = exercise_data.get("content_data", {})
        answers = exercise_data.get("answers")
        confidence = exercise_data.get("confidence")

        # Validate required fields
        if position is None:
            raise CommandError("Exercise missing 'position' field")
        if not kind:
            raise CommandError(f"Exercise at position {position} missing 'kind' field")
        if not skill:
            raise CommandError(
                f"Exercise at position {position} (kind: {kind}) missing 'skill' field"
            )
        if difficulty is None:
            raise CommandError(
                f"Exercise at position {position} (kind: {kind}) missing 'difficulty' field"
            )
        if not response_type:
            raise CommandError(
                f"Exercise at position {position} (kind: {kind}) missing 'response_type' field"
            )

        # Validate enum values
        try:
            Kind(kind)
        except ValueError:
            raise CommandError(
                f"Invalid kind '{kind}' at position {position}. "
                f"Valid options: {', '.join(k.value for k in Kind)}"
            )

        try:
            Skill(skill)
        except ValueError:
            raise CommandError(
                f"Invalid skill '{skill}' at position {position}. "
                f"Valid options: {', '.join(s.value for s in Skill)}"
            )

        try:
            ResponseType(response_type)
        except ValueError:
            raise CommandError(
                f"Invalid response_type '{response_type}' at position {position}. "
                f"Valid options: {', '.join(r.value for r in ResponseType)}"
            )

        # Validate difficulty is in range
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            raise CommandError(f"Difficulty must be integer 1-5, got {difficulty} at position {position}")

        # Generate exercise ID if needed
        exercise_id = exercise_data.get("id")
        if not exercise_id:
            exercise_id = f"{age_group}_position_{position:02d}_{kind}"

        # Validate content_data
        self._validate_content_data(content_data, response_type, position, kind)

        # Create or update exercise
        with transaction.atomic():
            AssessmentExcercise.objects.update_or_create(
                assessment=assessment,
                position=position,
                defaults={
                    "exercise_id": exercise_id,
                    "kind": kind,
                    "skill": skill,
                    "difficulty_level": difficulty,
                    "response_type": response_type,
                    "instruction": instruction,
                    "content_data": content_data,
                    "answers": answers or {},
                    "confidence": confidence,
                },
            )

    def _validate_content_data(
        self, content_data: dict, response_type: str, position: int, kind: str
    ) -> None:
        """Validate content_data structure based on response type."""
        if not isinstance(content_data, dict):
            raise CommandError(
                f"content_data must be a dict at position {position}, got {type(content_data)}"
            )

        if response_type == ResponseType.SINGLE_CHOICE_SET:
            items = content_data.get("items")
            if not isinstance(items, list) or not items:
                raise CommandError(
                    f"single_choice_set at position {position} requires non-empty 'items' array"
                )
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    raise CommandError(
                        f"Item {i} at position {position} is not a dict"
                    )
                if "options" not in item or not isinstance(item.get("options"), list):
                    raise CommandError(
                        f"Item {i} at position {position} missing 'options' array"
                    )

        elif response_type == ResponseType.SPOKEN:
            if kind == "word_reading_sample":
                sections = content_data.get("sections")
                if not isinstance(sections, list) or not sections:
                    raise CommandError(
                        f"word_reading_sample at position {position} requires 'sections' array"
                    )
            elif kind == "reading_fluency":
                passage_lines = content_data.get("passage_lines")
                if not isinstance(passage_lines, list) or not passage_lines:
                    raise CommandError(
                        f"reading_fluency at position {position} requires 'passage_lines' array"
                    )

        elif response_type == ResponseType.TYPED_TEXT:
            items = content_data.get("items")
            if not isinstance(items, list) or not items:
                raise CommandError(
                    f"typed_text at position {position} requires non-empty 'items' array"
                )
