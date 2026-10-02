from django.db import models
from django.contrib.postgres.fields import ArrayField

from user.choices import AgeGroup

# Create your models here.
class RealLifeSet(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    age_group = models.CharField(max_length=10, choices=AgeGroup.choices)
    category = models.TextField()
    
    class Meta:
        db_table = "real_life_sets"
        
class RealLifeSetExercise(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    real_life_set = models.ForeignKey(RealLifeSet, on_delete=models.CASCADE, related_name="exercises")
    title = models.CharField(max_length=255)
    context = models.CharField(max_length=255)
    information = ArrayField(models.TextField(), blank=True, default=list)
    question = models.TextField()
    options = ArrayField(models.TextField(), blank=True, default=list)
    correct_answer = ArrayField(models.TextField(), blank=True, default=list)
    
    class Meta:
        db_table = "real_life_set_exercises"
        
class RealLifeSetEvaluation(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    real_life_set = models.ForeignKey(RealLifeSet, on_delete=models.CASCADE, related_name="evaluations")
    user = models.ForeignKey("user.User", on_delete=models.CASCADE, related_name="real_life_set_evaluations")
    created_at = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField(default=dict)
    
    class Meta:
        db_table = "real_life_set_evaluations"