from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_userprofile_employment_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalarySlip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField()),
                ("month", models.PositiveSmallIntegerField()),
                ("base_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="底薪")),
                ("overtime_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="加班薪資")),
                ("work_hours", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="上班時數")),
                ("overtime_hours", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="加班時數")),
                ("base_pay", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="底薪薪資")),
                ("overtime_pay", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="加班薪資(合計)")),
                ("insurance_transfer", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="保險+轉帳")),
                ("performance_bonus", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="業績獎金")),
                ("labor_insurance", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="勞建保")),
                ("extra_health_insurance", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="多扣兩個月健保")),
                ("responsibility_bonus", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="責任獎金")),
                ("perfect_attendance", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="全勤")),
                ("total_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="總薪資")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="salary_slips", to="users.userprofile")),
            ],
            options={
                "ordering": ["-year", "-month", "profile__name"],
            },
        ),
        migrations.AddConstraint(
            model_name="salaryslip",
            constraint=models.UniqueConstraint(fields=("profile", "year", "month"), name="unique_salary_slip_per_month"),
        ),
    ]
