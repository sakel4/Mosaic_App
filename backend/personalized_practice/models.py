import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class LearnerSkillBaseline(models.Model):
    TREND_CHOICES = (
        ("improving", "Improving"),
        ("stable", "Stable"),
        ("declining", "Declining"),
        ("unknown", "Unknown"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skill_baselines",
    )
    skill = models.CharField(max_length=64)
    baseline_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    confidence = models.FloatField(
        default=0.35,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    direct_evidence = models.BooleanField(default=False)
    trend = models.CharField(max_length=16, choices=TREND_CHOICES, default="unknown")
    error_counts = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "skill"), name="uniq_user_skill_baseline"),
        ]
        indexes = [models.Index(fields=("user", "updated_at"), name="skill_user_updated_idx")]


class PracticeExercise(models.Model):
    AGE_GROUP_CHOICES = (
        ("under_12", "Under 12"),
        ("12_15", "12 to 15"),
        ("16_18", "16 to 18"),
        ("19_plus", "19 or older"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="practice_exercises",
    )
    age_group = models.CharField(max_length=16, choices=AGE_GROUP_CHOICES)
    bank_version = models.CharField(max_length=80)
    target_skill = models.CharField(max_length=64)
    secondary_skill = models.CharField(max_length=64, blank=True)
    difficulty = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    source_exercise_id = models.CharField(max_length=100)
    response_type = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    prompt = models.TextField()
    content_data = models.JSONField(default=dict)
    private_scoring = models.JSONField(default=dict)
    content_fingerprint = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=("user", "created_at"), name="practice_user_created_idx")]
