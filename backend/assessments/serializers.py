import random

from rest_framework import serializers

from .choices import ResponseType
from .models import Assessment, AssessmentExcercise

# content_data keys that hold interchangeable variants of an exercise.
VARIANT_KEYS = ("items", "sections")
# Section ids never served for spoken exercises.
EXCLUDED_SPOKEN_SECTION_IDS = ("pseudowords",)


class AssessmentExcerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentExcercise
        exclude = ("assessment", "answers")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        content = data.get("content_data")
        if isinstance(content, dict):
            content = dict(content)
            is_spoken = instance.response_type == ResponseType.SPOKEN
            for key in VARIANT_KEYS:
                variants = content.get(key)
                if key == "sections" and is_spoken and isinstance(variants, list):
                    variants = [
                        v for v in variants
                        if not (isinstance(v, dict) and v.get("id") in EXCLUDED_SPOKEN_SECTION_IDS)
                    ]
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
