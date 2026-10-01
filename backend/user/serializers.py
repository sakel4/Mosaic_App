from rest_framework import serializers

from .models import Profile, User


class ProfileAgeField(serializers.Field):
    age_field = serializers.IntegerField(min_value=0, max_value=120, allow_null=True)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, user):
        profile = getattr(user, "profile", None)
        return profile.age_years if profile is not None else None

    def to_internal_value(self, data):
        return self.age_field.run_validation(data)


class UserSerializer(serializers.ModelSerializer):
    age_years = ProfileAgeField(required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "age_years",
            "role",
            "assessment_completed",
            "created_at",
        )
        read_only_fields = ("id", "email", "role", "assessment_completed", "created_at")

    def update(self, instance, validated_data):
        age_years = validated_data.pop("age_years", serializers.empty)
        instance = super().update(instance, validated_data)
        if age_years is not serializers.empty:
            Profile.objects.update_or_create(user=instance, defaults={"age_years": age_years})
        return instance
