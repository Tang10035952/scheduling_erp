from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_userprofile_worker_profile_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="education_other",
            field=models.CharField(blank=True, max_length=10, verbose_name="學歷補充"),
        ),
    ]
