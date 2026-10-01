import os
from typing import Any, Mapping, Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from personalized_practice.domain import LearnerContext


class PracticeRepository(Protocol):
    def get_context(self, user_id: str) -> LearnerContext:
        """Return age, scored skills, trends, error counts, and recent exercise content."""
        ...

    def save_exercise(self, user_id: str, record: Mapping[str, Any]) -> None:
        """Persist private scoring and public exercise data before it is returned."""
        ...


def get_repository() -> PracticeRepository:
    provider_path = getattr(
        settings,
        "ONOMA_PRACTICE_REPOSITORY",
        os.getenv("ONOMA_PRACTICE_REPOSITORY"),
    )
    if not provider_path:
        raise ImproperlyConfigured(
            "Configure ONOMA_PRACTICE_REPOSITORY with a class implementing "
            "get_context(user_id) and save_exercise(user_id, record)."
        )
    provider_class = import_string(provider_path)
    return provider_class()
