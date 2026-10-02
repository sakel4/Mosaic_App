import random

from rest_framework import serializers

from .models import Assessment, AssessmentExcercise

# content_data keys that hold interchangeable variants of an exercise.
VARIANT_KEYS = ("items", "sections")


class AssessmentExcerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentExcercise
        exclude = ("assessment", "answers")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        content = data.get("content_data")
        if isinstance(content, dict):
            content = dict(content)
            for key in VARIANT_KEYS:
                variants = content.get(key)
                if isinstance(variants, list) and variants:
                    content[key] = [random.choice(variants)]
            data["content_data"] = content
        return data


class AssessmentSerializer(serializers.ModelSerializer):
    excercises = AssessmentExcerciseSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = (
            "id",
            "created_at",
            "age_group",
            "language",
            "assessment_type",
            "estimated_duration_seconds",
            "estimated_voice_duration_seconds",
            "excercises",
        )
