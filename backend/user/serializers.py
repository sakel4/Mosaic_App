from rest_framework import serializers

from .models import Preferences, Profile, Skill, User

SKILL_FIELDS = [f.name for f in Skill._meta.concrete_fields if f.name != "id"]


class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preferences
        exclude = ("id",)


class ProfileSerializer(serializers.ModelSerializer):
    preferences = PreferencesSerializer(read_only=True)
    current_focus = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ("age_group", "interests", "learning_goal", "current_focus", "preferences")

    def get_current_focus(self, profile):
        # Lowest-scoring skills; ties are all returned and a score of 0 counts.
        skills = profile.skills
        if skills is None:
            return []
        scores = {name: getattr(skills, name) for name in SKILL_FIELDS}
        scores = {name: score for name, score in scores.items() if score is not None}
        if not scores:
            return []
        lowest = min(scores.values())
        return [
            {"skill": name.replace("_", " ").title(), "score": score}
            for name, score in scores.items()
            if score == lowest
        ]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "assessment_completed", "created_at", "profile")
        read_only_fields = ("id", "email", "role", "assessment_completed", "created_at")

    def update(self, instance, validated_data):
        age_years = validated_data.pop("age_years", serializers.empty)
        instance = super().update(instance, validated_data)
        if age_years is not serializers.empty:
            Profile.objects.update_or_create(user=instance, defaults={"age_years": age_years})
        return instance
