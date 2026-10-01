from personalized_practice.domain import LearnerContext, PracticeDataError, SkillEvidence


AGE_GROUPS = ("under_12", "12_15", "16_18", "19_plus")


def age_group_for_age(age_years: int) -> str:
    if not 0 <= age_years <= 120:
        raise PracticeDataError("Learner age is outside the supported range.")
    if age_years < 12:
        return "under_12"
    if age_years <= 15:
        return "12_15"
    if age_years <= 18:
        return "16_18"
    return "19_plus"


def skill_priority(evidence: SkillEvidence) -> float:
    repeated_errors = sum(max(0, count - 1) for count in evidence.error_counts.values())
    error_bonus = min(20, repeated_errors * 5)
    evidence_bonus = 5 if evidence.direct_evidence else 0
    return (100 - evidence.baseline_score) * evidence.confidence + error_bonus + evidence_bonus


def choose_target_skill(context: LearnerContext, supported_skills: set[str] | None = None) -> str:
    eligible = {
        skill: evidence
        for skill, evidence in context.skills.items()
        if evidence.baseline_score is not None
        and (supported_skills is None or skill in supported_skills)
    }
    if not eligible:
        raise PracticeDataError("No scored skill evidence is available for practice selection.")

    def weakest(candidates: dict[str, SkillEvidence]) -> str:
        return min(candidates, key=lambda skill: (-skill_priority(candidates[skill]), skill))

    def strongest(candidates: dict[str, SkillEvidence]) -> str:
        return min(
            candidates,
            key=lambda skill: (-candidates[skill].baseline_score, -candidates[skill].confidence, skill),
        )

    slot = context.completed_practice_count % 20
    if slot < 12:
        return weakest(eligible)
    if slot < 17:
        improving = {skill: item for skill, item in eligible.items() if item.trend == "improving"}
        return weakest(improving or eligible)

    maintenance = {skill: item for skill, item in eligible.items() if item.baseline_score >= 60}
    return strongest(maintenance or eligible)


def difficulty_for_score(baseline_score: float, bank_difficulty: int) -> int:
    if baseline_score < 40:
        adjusted = bank_difficulty - 1
    elif baseline_score < 60:
        adjusted = bank_difficulty
    elif baseline_score <= 80:
        adjusted = bank_difficulty + 1
    else:
        adjusted = bank_difficulty + 2
    return max(1, min(5, adjusted))
