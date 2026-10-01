from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("user", "0007_remove_profile_age_years")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
    ]
