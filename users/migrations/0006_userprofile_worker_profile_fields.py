from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_userprofile_primary_store"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="real_name",
            field=models.CharField(blank=True, max_length=50, verbose_name="真實姓名"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="gender",
            field=models.CharField(blank=True, max_length=2, verbose_name="性別"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="birthday",
            field=models.DateField(blank=True, null=True, verbose_name="生日"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="id_number",
            field=models.CharField(blank=True, max_length=10, verbose_name="身分證字號"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="marital_status",
            field=models.CharField(blank=True, max_length=10, verbose_name="婚姻狀況"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="education",
            field=models.CharField(blank=True, max_length=20, verbose_name="學歷"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="education_other",
            field=models.CharField(blank=True, max_length=100, verbose_name="學歷補充"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="contact_address",
            field=models.CharField(blank=True, max_length=255, verbose_name="通訊地址"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="registered_address",
            field=models.CharField(blank=True, max_length=255, verbose_name="戶籍地址"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="mobile_phone",
            field=models.CharField(blank=True, max_length=20, verbose_name="手機電話"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="emergency_contact",
            field=models.TextField(blank=True, verbose_name="緊急聯絡人"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="work_experience",
            field=models.TextField(blank=True, verbose_name="工作經歷"),
        ),
        migrations.CreateModel(
            name="WorkerDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("id_card", "身分證"), ("driver_license", "駕照"), ("bankbook", "存摺")], max_length=20)),
                ("file", models.FileField(upload_to="worker_documents/")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="documents", to="users.userprofile")),
            ],
        ),
    ]
