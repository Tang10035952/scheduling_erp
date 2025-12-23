from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0003_schedulingwindow_workavailability"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="schedulingwindow",
            constraint=models.CheckConstraint(
                check=Q(end_date__gte=F("start_date")),
                name="schedulingwindow_end_date_gte_start_date",
            ),
        ),
    ]
