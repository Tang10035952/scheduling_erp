from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_alter_workerdocument_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="must_reset_password",
            field=models.BooleanField(default=False),
        ),
    ]
