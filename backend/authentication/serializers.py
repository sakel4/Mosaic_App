from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from user.models import Preferences, Profile, Skill
from user.serializers import SKILL_FIELDS

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "role")
        read_only_fields = ("id", "role")

    def validate(self, attrs):
        validate_password(attrs["password"], user=User(**{k: v for k, v in attrs.items() if k != "password"}))
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # Public signup always creates learners; admins are created via admin/createsuperuser.
        user = User.objects.create_user(**validated_data)
        skills = Skill.objects.create(**{name: 0 for name in SKILL_FIELDS})
        Profile.objects.create(user=user, skills=skills, preferences=Preferences.objects.create())
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims are readable by anyone holding the token; never put secrets here.
        token["email"] = user.email
        token["role"] = user.role
        return token
