import hashlib
import json
import uuid
from typing import Any, Mapping

from personalized_practice.bank import load_age_bank, public_content, select_seed, supported_skills
from personalized_practice.domain import LearnerContext
from personalized_practice.selection import (
    choose_secondary_skill,
    choose_target_skill,
    difficulty_for_score,
)


class PracticeOrchestrator:
    def __init__(self, repository, generator):
        self.repository = repository
        self.generator = generator

    def next_exercise(self, user_id: str) -> dict[str, Any]:
        context = self.repository.get_context(user_id)
        if not isinstance(context, LearnerContext):
            context = LearnerContext.from_mapping(context)
        age_group = context.age_group
        age_skills = supported_skills(age_group)
        target_skill = choose_target_skill(context, age_skills)
        secondary_skill = choose_secondary_skill(context, target_skill, age_skills)
        evidence = context.skills[target_skill]
        learner_profile = {
            "age_group": age_group,
            "skills": {
                skill: {
                    "mastery": item.baseline_score / 100,
                    "confidence": item.confidence,
                    "direct_evidence": item.direct_evidence,
                    "trend": item.trend,
                    "metrics": dict(item.metrics),
                    "error_counts": dict(item.error_counts),
                    "error_patterns": sorted(
                        error for error, count in item.error_counts.items() if count > 0
                    ),
                }
                for skill, item in context.skills.items()
            },
        }
        recent_source_ids = {
            str(item["source_exercise_id"])
            for item in context.recent_exercises
            if item.get("source_exercise_id")
        }
        seed = select_seed(age_group, target_skill, recent_source_ids)
        difficulty = difficulty_for_score(evidence.baseline_score, int(seed["difficulty"]))
        generated = self.generator.generate(
            age_group=age_group,
            skill=target_skill,
            difficulty=difficulty,
            seed=seed,
            recent_exercises=context.recent_exercises,
            secondary_skill=secondary_skill,
            learner_profile=learner_profile,
        )
        exercise_id = str(uuid.uuid4())
        fingerprint = hashlib.sha256(
            json.dumps(generated["content_data"], sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        record = {
            "id": exercise_id,
            "age_group": age_group,
            "bank_version": load_age_bank(age_group)["assessment_version"],
            "target_skill": target_skill,
            "secondary_skill": secondary_skill or "",
            "difficulty": difficulty,
            "source_exercise_id": seed["id"],
            "response_type": seed["response_type"],
            "title": generated["title"],
            "instructions": generated["instructions"],
            "prompt": generated["prompt"],
            "content_data": generated["content_data"],
            "private_scoring": generated["private_scoring"],
            "content_fingerprint": fingerprint,
        }
        self.repository.save_exercise(user_id, record)
        return {
            "exercise_id": exercise_id,
            "age_group": age_group,
            "target_skill": target_skill,
            "secondary_skill": secondary_skill,
            "difficulty": difficulty,
            "response_type": seed["response_type"],
            "exercise": {
                "title": generated["title"],
                "instructions": generated["instructions"],
                "prompt": generated["prompt"],
                "content_data": public_content(generated["content_data"]),
            },
        }
