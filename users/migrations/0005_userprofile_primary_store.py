from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_userprofile_sort_order"),
        ("scheduling", "0007_store_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="primary_store",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="primary_workers",
                to="scheduling.store",
                verbose_name="主要店別",
            ),
        ),
    ]
