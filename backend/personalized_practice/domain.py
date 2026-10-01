from dataclasses import dataclass, field
from typing import Any, Mapping


class PracticeDataError(Exception):
    pass


AGE_GROUPS = ("under_12", "12_15", "16_18", "19_plus")


@dataclass(frozen=True)
class SkillEvidence:
    baseline_score: float
    confidence: float
    direct_evidence: bool = False
    trend: str = "unknown"
    error_counts: Mapping[str, int] = field(default_factory=dict)
    metrics: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SkillEvidence":
        score = float(value["baseline_score"])
        confidence = float(value.get("confidence", 0.35))
        if not 0 <= score <= 100:
            raise PracticeDataError("Skill baseline_score must be between 0 and 100.")
        if not 0 <= confidence <= 1:
            raise PracticeDataError("Skill confidence must be between 0 and 1.")
        errors = value.get("error_counts", {})
        if not isinstance(errors, Mapping):
            raise PracticeDataError("Skill error_counts must be an object.")
        metrics = value.get("metrics", {})
        if not isinstance(metrics, Mapping):
            raise PracticeDataError("Skill metrics must be an object.")
        trend = str(value.get("trend", "unknown"))
        if trend not in {"improving", "stable", "declining", "unknown"}:
            raise PracticeDataError("Unsupported skill trend.")
        return cls(
            baseline_score=score,
            confidence=confidence,
            direct_evidence=bool(value.get("direct_evidence", False)),
            trend=trend,
            error_counts={str(name): max(0, int(count)) for name, count in errors.items()},
            metrics=dict(metrics),
        )


@dataclass(frozen=True)
class LearnerContext:
    age_group: str
    skills: Mapping[str, SkillEvidence]
    completed_practice_count: int = 0
    recent_exercises: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LearnerContext":
        try:
            age_group = str(value["age_group"])
            raw_skills = value["skills"]
        except (KeyError, TypeError, ValueError) as exc:
            raise PracticeDataError("Learner context requires age_group and skills.") from exc
        if age_group not in AGE_GROUPS:
            raise PracticeDataError("Learner age_group is not supported.")
        if not isinstance(raw_skills, Mapping):
            raise PracticeDataError("Learner skills must be an object keyed by skill.")

        parsed_skills = {}
        for skill, evidence in raw_skills.items():
            if not isinstance(evidence, Mapping) or evidence.get("baseline_score") is None:
                continue
            parsed_skills[str(skill)] = SkillEvidence.from_mapping(evidence)

        recent = value.get("recent_exercises", ())
        if not isinstance(recent, (list, tuple)):
            raise PracticeDataError("recent_exercises must be a list.")
        return cls(
            age_group=age_group,
            skills=parsed_skills,
            completed_practice_count=max(0, int(value.get("completed_practice_count", 0))),
            recent_exercises=tuple(item for item in recent if isinstance(item, Mapping)),
        )
