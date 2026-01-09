from django.db import migrations, models


def set_salary_slip_defaults(apps, schema_editor):
    SalarySlip = apps.get_model("users", "SalarySlip")
    fields = [
        "base_salary",
        "overtime_salary",
        "work_hours",
        "overtime_hours",
        "base_pay",
        "overtime_pay",
        "insurance_transfer",
        "performance_bonus",
        "labor_insurance",
        "extra_health_insurance",
        "responsibility_bonus",
        "perfect_attendance",
        "total_salary",
    ]
    for field in fields:
        SalarySlip.objects.filter(**{f"{field}__isnull": True}).update(**{field: 0})


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_userprofile_pay_type"),
    ]

    operations = [
        migrations.RunPython(set_salary_slip_defaults, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="salaryslip",
            name="base_salary",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="底薪"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="overtime_salary",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="加班薪資"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="work_hours",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="上班時數"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="overtime_hours",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="加班時數"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="base_pay",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, verbose_name="底薪薪資"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="overtime_pay",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, verbose_name="加班薪資(合計)"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="insurance_transfer",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="保險+轉帳"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="performance_bonus",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="業績獎金"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="labor_insurance",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="勞建保"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="extra_health_insurance",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="多扣兩個月健保"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="responsibility_bonus",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="責任獎金"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="perfect_attendance",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name="全勤"),
        ),
        migrations.AlterField(
            model_name="salaryslip",
            name="total_salary",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, verbose_name="總薪資"),
        ),
    ]
