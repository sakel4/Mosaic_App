import os
from typing import Any, Mapping, Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from personalized_practice.domain import LearnerContext
from personalized_practice.models import LearnerSkillBaseline, PracticeExercise
from personalized_practice.domain import PracticeDataError
from user.models import Profile


class PracticeRepository(Protocol):
    def get_context(self, user_id: str) -> LearnerContext:
        """Return age, scored skills, trends, error counts, and recent exercise content."""
        ...

    def save_exercise(self, user_id: str, record: Mapping[str, Any]) -> None:
        """Persist private scoring and public exercise data before it is returned."""
        ...


class DjangoPracticeRepository:
    def get_context(self, user_id: str) -> LearnerContext:
        profile = Profile.objects.filter(user_id=user_id).only("age_group").first()
        if profile is None or not profile.age_group:
            raise PracticeDataError("Set the learner's age group in their profile before requesting practice.")

        skills = {
            baseline.skill: {
                "baseline_score": baseline.baseline_score,
                "confidence": baseline.confidence,
                "direct_evidence": baseline.direct_evidence,
                "trend": baseline.trend,
                "error_counts": baseline.error_counts,
                "metrics": baseline.metrics,
                "metrics": baseline.metrics,
            }
            for baseline in LearnerSkillBaseline.objects.filter(user_id=user_id)
            if baseline.baseline_score is not None
        }
        exercises = list(
            PracticeExercise.objects.filter(user_id=user_id)
            .order_by("-created_at")
            .values("source_exercise_id", "title", "prompt", "content_data")[:5]
        )
        completed_count = PracticeExercise.objects.filter(user_id=user_id).count()
        return LearnerContext.from_mapping(
            {
                "age_group": profile.age_group,
                "skills": skills,
                "completed_practice_count": completed_count,
                "recent_exercises": exercises,
            }
        )

    def save_exercise(self, user_id: str, record: Mapping[str, Any]) -> None:
        PracticeExercise.objects.create(
            id=record["id"],
            user_id=user_id,
            age_group=record["age_group"],
            bank_version=record["bank_version"],
            target_skill=record["target_skill"],
            secondary_skill=record.get("secondary_skill", ""),
            difficulty=record["difficulty"],
            source_exercise_id=record["source_exercise_id"],
            response_type=record["response_type"],
            title=record["title"],
            instructions=record["instructions"],
            prompt=record["prompt"],
            content_data=record["content_data"],
            private_scoring=record["private_scoring"],
            content_fingerprint=record["content_fingerprint"],
        )


def get_repository() -> PracticeRepository:
    provider_path = getattr(
        settings,
        "ONOMA_PRACTICE_REPOSITORY",
        os.getenv("ONOMA_PRACTICE_REPOSITORY"),
    )
    if not provider_path:
        return DjangoPracticeRepository()
    provider_class = import_string(provider_path)
    return provider_class()
