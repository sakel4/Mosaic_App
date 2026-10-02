from rest_framework import serializers

from .models import RealLifeSet, RealLifeSetExercise


class RealLifeSetExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealLifeSetExercise
        exclude = ("real_life_set",)


class EvaluateRealLifeSetSerializer(serializers.Serializer):
    real_life_set_id = serializers.CharField(max_length=100)
    # Keyed by exercise id; true means the learner answered correctly.
    answers = serializers.DictField(child=serializers.BooleanField(), allow_empty=False)


class RealLifeSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealLifeSet
        fields = ("id", "category", "age_group")

    def to_representation(self, instance):
        exercises = RealLifeSetExerciseSerializer(instance.exercises.order_by("id"), many=True).data
        return {
            "id": instance.id,
            "category": instance.category,
            "age_group": {instance.age_group: exercises},
        }
