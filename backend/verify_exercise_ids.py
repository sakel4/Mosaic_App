#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from assessments.models import AssessmentExcercise

exercises = AssessmentExcercise.objects.filter(
    assessment__age_group='19_plus'
).order_by('position').values('position', 'kind', 'exercise_id')

print("Exercise IDs for 19_plus Assessment:\n")
for ex in exercises:
    print(f"{ex['position']}: {ex['kind']} -> {ex['exercise_id']}")
