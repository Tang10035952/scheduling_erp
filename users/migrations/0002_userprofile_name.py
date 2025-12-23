from django.db import migrations, models


def populate_name(apps, schema_editor):
    UserProfile = apps.get_model("users", "UserProfile")
    for profile in UserProfile.objects.select_related("user").all():
        user = profile.user
        combined = f"{user.last_name}{user.first_name}".strip()
        profile.name = combined or user.username
        profile.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="name",
            field=models.CharField(
                verbose_name="名稱",
                max_length=50,
                blank=True,
                default="",
            ),
        ),
        migrations.RunPython(populate_name, migrations.RunPython.noop),
    ]
