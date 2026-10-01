from django.db import transaction
from rest_framework import serializers

from .models import Preferences, Profile, Skill, User

SKILL_FIELDS = [f.name for f in Skill._meta.concrete_fields if f.name != "id"]


class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preferences
        exclude = ("id",)


class ProfileSerializer(serializers.ModelSerializer):
    preferences = PreferencesSerializer(required=False)
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
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "role",
            "assessment_completed", "on_bording_completed", "created_at", "profile",
        )
        read_only_fields = ("id", "email", "role", "created_at")

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        preferences_data = profile_data.pop("preferences", {})
        instance = super().update(instance, validated_data)

        try:
            profile = instance.profile
        except Profile.DoesNotExist:
            profile = Profile(user=instance)

        # Only keys present in the request are applied.
        for attr, value in profile_data.items():
            setattr(profile, attr, value)

        if preferences_data:
            if profile.preferences is None:
                profile.preferences = Preferences.objects.create(**preferences_data)
            else:
                for attr, value in preferences_data.items():
                    setattr(profile.preferences, attr, value)
                profile.preferences.save()

        profile.save()
        return instance
