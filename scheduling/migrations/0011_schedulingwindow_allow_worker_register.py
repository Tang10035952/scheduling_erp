from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0010_shift_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedulingwindow",
            name="allow_worker_register",
            field=models.BooleanField(default=False),
        ),
    ]
