from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0007_store_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedulingwindow",
            name="allow_worker_edit_shifts",
            field=models.BooleanField(default=False),
        ),
    ]
