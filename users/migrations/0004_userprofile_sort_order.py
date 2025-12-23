from django.db import migrations, models


def set_initial_order(apps, schema_editor):
    UserProfile = apps.get_model("users", "UserProfile")
    for idx, profile in enumerate(UserProfile.objects.order_by("id"), start=1):
        profile.sort_order = idx
        profile.save(update_fields=["sort_order"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_userprofile_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(set_initial_order, migrations.RunPython.noop),
    ]
