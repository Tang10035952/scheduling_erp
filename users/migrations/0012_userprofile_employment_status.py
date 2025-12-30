from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_userprofile_must_reset_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="employment_status",
            field=models.CharField(
                choices=[("active", "在職"), ("inactive", "離職")],
                default="active",
                max_length=10,
                verbose_name="在職狀態",
            ),
        ),
    ]
