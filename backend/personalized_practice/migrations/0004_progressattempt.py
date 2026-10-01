import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("personalized_practice", "0003_practiceexercise_secondary_skill"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProgressAttempt",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("client_id", models.UUIDField()),
                ("exercise_id", models.CharField(max_length=100)),
                ("skill", models.CharField(max_length=100)),
                ("correct", models.BooleanField()),
                ("response_time", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("user", "client_id"), name="uniq_progress_submission")],
                "indexes": [models.Index(fields=("user", "created_at"), name="progress_user_created_idx")],
            },
        ),
    ]
