from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    LEARNER = "learner", "Learner"


class AgeGroup(models.TextChoices):
    UNDER_12 = "under_12", "Under 12"
    AGE_12_15 = "12_15", "12-15"
    AGE_16_18 = "16_18", "16-18"
    AGE_19_PLUS = "19_plus", "19+"


class ReadingFont(models.TextChoices):
    DEFAULT = "default", "Default"
    LEXEND = "lexend", "Lexend"
    OPENS_DYSLEXIC = "opens_dyslexic", "OpenDyslexic"


class FontSize(models.TextChoices):
    COMFORTABLE = "comfortable", "Comfortable"
    LARGE = "large", "Large"
    XLARGE = "x_large", "Extra Large"


class LineSpacing(models.TextChoices):
    STANDARD = "standard", "Standard"
    RELAXED = "relaxed", "Relaxed"
    WIDE = "wide", "Wide"


class LetterSpacing(models.TextChoices):
    STANDARD = "standard", "Standard"
    WIDE = "wide", "Wide"
    WIDER = "wider", "Wider"


class Theme(models.TextChoices):
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"
