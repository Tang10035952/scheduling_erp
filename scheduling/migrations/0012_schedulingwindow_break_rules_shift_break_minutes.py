from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0011_schedulingwindow_allow_worker_register"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedulingwindow",
            name="break_rules",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="shift",
            name="break_minutes",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="休息時間(分鐘)"),
        ),
    ]
