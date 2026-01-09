from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_salary_slip"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="pay_type",
            field=models.CharField(
                choices=[("hourly", "計時"), ("salaried", "正職")],
                default="hourly",
                max_length=10,
                verbose_name="薪資類型",
            ),
        ),
    ]
