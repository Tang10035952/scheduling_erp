from django.db import migrations, models


def create_default_store(apps, schema_editor):
    Store = apps.get_model("scheduling", "Store")
    Shift = apps.get_model("scheduling", "Shift")
    default_store, _ = Store.objects.get_or_create(name="主店")
    Shift.objects.filter(store__isnull=True).update(store=default_store)


def delete_default_store(apps, schema_editor):
    Store = apps.get_model("scheduling", "Store")
    Store.objects.filter(name="主店").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0005_schedulingwindow_allow_worker_view"),
    ]

    operations = [
        migrations.CreateModel(
            name="Store",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="shift",
            name="store",
            field=models.ForeignKey(null=True, on_delete=models.PROTECT, related_name="shifts", to="scheduling.store", verbose_name="店別"),
        ),
        migrations.RunPython(create_default_store, delete_default_store),
        migrations.AlterField(
            model_name="shift",
            name="store",
            field=models.ForeignKey(on_delete=models.PROTECT, related_name="shifts", to="scheduling.store", verbose_name="店別"),
        ),
    ]
