from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0006_store_and_shift_store"),
    ]

    operations = [
        migrations.AddField(
            model_name="store",
            name="color",
            field=models.CharField(default="#cfe8ff", max_length=7),
        ),
    ]
