from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0004_schedulingwindow_end_date_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedulingwindow",
            name="allow_worker_view",
            field=models.BooleanField(default=False),
        ),
    ]
