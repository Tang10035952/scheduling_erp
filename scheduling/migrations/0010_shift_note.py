from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0009_shift_store_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="note",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="備註"),
        ),
    ]
