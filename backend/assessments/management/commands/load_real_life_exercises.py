import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from assessments.models import RealLifeExercise
from assessments.real_life import RealLifeExerciseSerializer


class Command(BaseCommand):
    help = "Import an age_groups JSON real-life exercise bank."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(Path(settings.BASE_DIR) / "Exercises-AI" / "real_life_exercises.json"))

    def handle(self, *args, **options):
        try:
            bank = json.loads(Path(options["path"]).read_text(encoding="utf-8-sig"))
            groups = bank["age_groups"]
            if not isinstance(groups, dict):
                raise ValueError("age_groups must be an object")
            rows = []
            seen = set()
            for age_group, exercises in groups.items():
                # Scenario banks call the adult group 18_plus; the profile model uses 19_plus.
                age_group = "19_plus" if age_group == "18_plus" else age_group
                if not isinstance(exercises, list):
                    raise ValueError("Each age group must contain an exercise list")
                for exercise in exercises:
                    serializer = RealLifeExerciseSerializer(data={**exercise, "age_group": age_group})
                    serializer.is_valid(raise_exception=True)
                    data = dict(serializer.validated_data)
                    if data["id"] in seen:
                        raise ValueError(f"Duplicate exercise id: {data['id']}")
                    seen.add(data["id"])
                    rows.append(data)
        except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
            raise CommandError(str(exc)) from exc

        with transaction.atomic():
            for data in rows:
                exercise_id = data.pop("id")
                RealLifeExercise.objects.update_or_create(pk=exercise_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(rows)} real-life exercises."))
