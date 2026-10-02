from rest_framework import serializers

from .models import RealLifeSet, RealLifeSetExercise


class RealLifeSetExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealLifeSetExercise
        exclude = ("real_life_set", "correct_answer")


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
