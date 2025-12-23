from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_userprofile_education_other_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="emergency_contact_name",
            field=models.CharField(blank=True, max_length=10, verbose_name="緊急聯絡人姓名"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="emergency_contact_relation",
            field=models.CharField(blank=True, max_length=10, verbose_name="緊急聯絡人關係"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="emergency_contact_phone",
            field=models.CharField(blank=True, max_length=10, verbose_name="緊急聯絡人電話"),
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="emergency_contact",
        ),
    ]
