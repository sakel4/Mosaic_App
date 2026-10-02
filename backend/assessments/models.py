import uuid

from django.db import models
from django.contrib.postgres.fields import ArrayField

from user.choices import AgeGroup
from .choices import AssessmentType, Kind, ResponseType, Skill
    

# Create your models here.
class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    age_group = models.CharField(max_length=10, choices=AgeGroup.choices, blank=True, default="")
    language = models.CharField(max_length=10, default="en")
    estimated_duration_seconds = models.IntegerField(blank=True, null=True)
    estimated_voice_duration_seconds = models.IntegerField(blank=True, null=True)
    assessment_type = models.CharField(max_length=100, choices=AssessmentType.choices, blank=True, default="")
    
    class Meta:
        db_table = "assessments"
        

class AssessmentExcercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="excercises")
    position = models.IntegerField()
    kind = models.CharField(max_length=100, choices=Kind.choices, blank=True, default="")
    skill = models.CharField(max_length=100, choices=Skill.choices, blank=True, default="")
    difficulty_level = models.IntegerField(blank=True, null=True)
    response_type = models.CharField(max_length=100, choices=ResponseType.choices, blank=True, default="")
    instruction = models.TextField(blank=True, default="")
    content_data = models.JSONField(blank=True, null=True)
    answers = models.JSONField(blank=True, null=True)
    # confidence field is 0 to 100
    confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    class Meta:
        db_table = "assessment_excercises"
        
class SkillHistory(models.Model):
        phonological_awareness = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        letter_sound_association = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        decoding = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        word_recognition = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        naming_speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        reading_fluency = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        spelling = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        comprehension = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        working_memory = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
        created_at = models.DateTimeField(auto_now_add=True)

class AssessmentEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="evaluations")
    answers = models.JSONField(blank=True, null=True)
    user_id = models.ForeignKey("user.User", on_delete=models.CASCADE, related_name="assessment_evaluations")
    error_types = ArrayField(models.TextField(), blank=True, default=list)
    updated_skills = models.OneToOneField(SkillHistory, on_delete=models.CASCADE, related_name="assessment_evaluation", null=True, blank=True) 
    
    class Meta:
        db_table = "assessment_evaluations"
        
