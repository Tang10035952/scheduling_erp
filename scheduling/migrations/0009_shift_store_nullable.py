from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0008_schedulingwindow_allow_worker_edit_shifts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shift",
            name="store",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name="shifts",
                to="scheduling.store",
                verbose_name="店別",
            ),
        ),
    ]
