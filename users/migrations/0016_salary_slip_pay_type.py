from django.db import migrations, models


def copy_pay_type_from_profile(apps, schema_editor):
    SalarySlip = apps.get_model("users", "SalarySlip")
    for slip in SalarySlip.objects.select_related("profile").all():
        profile = getattr(slip, "profile", None)
        if profile and hasattr(profile, "pay_type"):
            slip.pay_type = profile.pay_type
            slip.save(update_fields=["pay_type"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_salary_slip_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="salaryslip",
            name="pay_type",
            field=models.CharField(
                blank=True,
                choices=[("hourly", "計時"), ("salaried", "正職")],
                default="hourly",
                max_length=10,
                verbose_name="薪資方式",
            ),
        ),
        migrations.RunPython(copy_pay_type_from_profile, migrations.RunPython.noop),
    ]
