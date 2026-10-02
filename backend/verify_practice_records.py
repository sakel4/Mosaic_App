from personalized_practice.models import PracticeExercise, ProgressAttempt, LearnerSkillBaseline
from user.models import User

user = User.objects.get(email="emmbamp@gmail.com")

print("=" * 60)
print("RECENT PRACTICE EXERCISES")
print("=" * 60)
exercises = PracticeExercise.objects.filter(user=user).order_by('-created_at')[:3]
for ex in exercises:
    print(f"\nExercise ID: {ex.id}")
    print(f"  Skill: {ex.target_skill}")
    print(f"  Difficulty: {ex.difficulty}")
    print(f"  Title: {ex.title}")
    print(f"  Private Scoring Keys: {list(ex.private_scoring.get('answer_key', {}).keys())}")
    print(f"  Created: {ex.created_at}")

print("\n" + "=" * 60)
print("RECENT PROGRESS ATTEMPTS")
print("=" * 60)
attempts = ProgressAttempt.objects.filter(user=user).order_by('-created_at')[:5]
for attempt in attempts:
    print(f"\nAttempt ID: {attempt.id}")
    print(f"  Exercise: {attempt.exercise_id}")
    print(f"  Skill: {attempt.skill}")
    print(f"  Correct: {attempt.correct}")
    print(f"  Created: {attempt.created_at}")

print("\n" + "=" * 60)
print("LEARNER SKILL BASELINES")
print("=" * 60)
baselines = LearnerSkillBaseline.objects.filter(user=user)
for baseline in baselines:
    print(f"\nSkill: {baseline.skill}")
    print(f"  Baseline Score: {baseline.baseline_score}%")
    print(f"  Confidence: {baseline.confidence}")
    print(f"  Direct Evidence: {baseline.direct_evidence}")
    print(f"  Trend: {baseline.trend}")
    print(f"  Metrics: {baseline.metrics}")
    print(f"  Updated: {baseline.updated_at}")

print("\n" + "=" * 60)
print("✅ Database verification complete")
print("=" * 60)
