import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from .choices import AgeGroup, FontSize, LetterSpacing, LineSpacing, ReadingFont, Role, Theme


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.LEARNER)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["role"] != Role.ADMIN or not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have role=admin and is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class BaseUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Abstract identity shared by all users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LEARNER)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        abstract = True

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_staff(self):
        # Django admin requires this attribute; admins get site access.
        return self.is_admin

    @property
    def is_learner(self):
        return self.role == Role.LEARNER


class User(BaseUser):
    assessment_completed = models.BooleanField(default=False)
    from django.core.validators import MaxValueValidator, MinValueValidator
    class Meta:
        db_table = "users"


# User complementary models
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    age_group = models.CharField(max_length=10, choices=AgeGroup.choices, blank=True, default="")
    interests = ArrayField(models.TextField(), blank=True, default=list)
    learning_goal = models.TextField(blank=True, default="")
    skills = models.OneToOneField("Skill", on_delete=models.CASCADE, related_name="profile", null=True, blank=True)
    preferences = models.OneToOneField("Preferences", on_delete=models.CASCADE, related_name="profile", null=True, blank=True)

class Skill(models.Model):
    phonological_awareness = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    letter_sound_association = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    decoding = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    word_recognition = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    naming_speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reading_fluency = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    spelling = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comprehension = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    working_memory = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

class Preferences(models.Model):
    # Add preference fields here
    reading_font = models.CharField(max_length=100, choices=ReadingFont.choices, default=ReadingFont.DEFAULT)
    font_size = models.CharField(max_length=100, choices=FontSize.choices, default=FontSize.COMFORTABLE)
    letter_spacing = models.CharField(max_length=100, choices=LetterSpacing.choices, default=LetterSpacing.STANDARD)
    line_spacing = models.CharField(max_length=100, choices=LineSpacing.choices, default=LineSpacing.STANDARD)
    text_to_speech = models.BooleanField(default=False)
    current_line_highlight = models.BooleanField(default=True)
    reduced_clutter = models.BooleanField(default=False)
    theme = models.CharField(max_length=100, choices=Theme.choices, default=Theme.LIGHT)
