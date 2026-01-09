from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver

from django.core.files.storage import default_storage

class UserProfile(models.Model):
    USER_ROLES = (
        ('worker', '員工'),
        ('manager', '店長'),
        ('supervisor', '主管'),
    )
    EMPLOYMENT_STATUS = (
        ("active", "在職"),
        ("inactive", "離職"),
    )
    PAY_TYPES = (
        ("hourly", "計時"),
        ("salaried", "正職"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField("名稱", max_length=50, blank=True)
    real_name = models.CharField("真實姓名", max_length=50, blank=True)
    gender = models.CharField("性別", max_length=2, blank=True)
    birthday = models.DateField("生日", null=True, blank=True)
    id_number = models.CharField("身分證字號", max_length=10, blank=True)
    marital_status = models.CharField("婚姻狀況", max_length=10, blank=True)
    education = models.CharField("學歷", max_length=20, blank=True)
    education_other = models.CharField("學歷補充", max_length=10, blank=True)
    contact_address = models.CharField("通訊地址", max_length=255, blank=True)
    registered_address = models.CharField("戶籍地址", max_length=255, blank=True)
    mobile_phone = models.CharField("手機電話", max_length=20, blank=True)
    emergency_contact_name = models.CharField("緊急聯絡人姓名", max_length=10, blank=True)
    emergency_contact_relation = models.CharField("緊急聯絡人關係", max_length=10, blank=True)
    emergency_contact_phone = models.CharField("緊急聯絡人電話", max_length=10, blank=True)
    work_experience = models.TextField("工作經歷", blank=True)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='worker')
    sort_order = models.PositiveIntegerField(default=0)
    must_reset_password = models.BooleanField(default=False)
    primary_store = models.ForeignKey(
        "scheduling.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_workers",
        verbose_name="店別",
    )
    employment_status = models.CharField(
        "在職狀態",
        max_length=10,
        choices=EMPLOYMENT_STATUS,
        default="active",
    )
    pay_type = models.CharField(
        "薪資類型",
        max_length=10,
        choices=PAY_TYPES,
        default="hourly",
    )

    def is_manager(self):
        return self.role in {'manager', 'supervisor'}

    def is_store_manager(self):
        return self.role == 'manager'

    def display_name(self):
        return self.name or self.user.username

    def age(self):
        if not self.birthday:
            return None
        today = timezone.localdate()
        years = today.year - self.birthday.year
        if (today.month, today.day) < (self.birthday.month, self.birthday.day):
            years -= 1
        return years

    def missing_required_info(self):
        required_fields = [
            self.name,
            self.real_name,
            self.gender,
            self.birthday,
            self.id_number,
            self.marital_status,
            self.education,
            self.contact_address,
            self.registered_address,
            self.mobile_phone,
            self.emergency_contact_name,
            self.emergency_contact_relation,
            self.emergency_contact_phone,
            self.work_experience,
        ]
        if any(not value for value in required_fields):
            return True
        if self.education == "其他" and not self.education_other:
            return True
        return False
    
    def __str__(self):
        return self.display_name()


class WorkerDocument(models.Model):
    CATEGORY_CHOICES = (
        ("id_card_front", "身分證正面"),
        ("id_card_back", "身分證反面"),
        ("driver_license", "駕照"),
        ("bankbook", "存摺"),
        ("other", "其他"),
    )
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="documents")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to="worker_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile_id}:{self.category}"


class SalarySlip(models.Model):
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="salary_slips",
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    pay_type = models.CharField(
        "薪資方式",
        max_length=10,
        choices=UserProfile.PAY_TYPES,
        default="hourly",
        blank=True,
    )
    base_salary = models.DecimalField("底薪", max_digits=10, decimal_places=2, default=0, blank=True)
    overtime_salary = models.DecimalField("加班薪資", max_digits=10, decimal_places=2, default=0, blank=True)
    work_hours = models.DecimalField("上班時數", max_digits=10, decimal_places=2, default=0, blank=True)
    overtime_hours = models.DecimalField("加班時數", max_digits=10, decimal_places=2, default=0, blank=True)
    base_pay = models.DecimalField("底薪薪資", max_digits=12, decimal_places=2, default=0, blank=True)
    overtime_pay = models.DecimalField("加班薪資(合計)", max_digits=12, decimal_places=2, default=0, blank=True)
    insurance_transfer = models.DecimalField("保險+轉帳", max_digits=10, decimal_places=2, default=0, blank=True)
    performance_bonus = models.DecimalField("業績獎金", max_digits=10, decimal_places=2, default=0, blank=True)
    labor_insurance = models.DecimalField("勞建保", max_digits=10, decimal_places=2, default=0, blank=True)
    extra_health_insurance = models.DecimalField("多扣兩個月健保", max_digits=10, decimal_places=2, default=0, blank=True)
    responsibility_bonus = models.DecimalField("責任獎金", max_digits=10, decimal_places=2, default=0, blank=True)
    perfect_attendance = models.DecimalField("全勤", max_digits=10, decimal_places=2, default=0, blank=True)
    total_salary = models.DecimalField("總薪資", max_digits=12, decimal_places=2, default=0, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month", "profile__name"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "year", "month"], name="unique_salary_slip_per_month"),
        ]

    def __str__(self):
        return f"{self.profile.display_name()} {self.year}-{self.month:02d}"


@receiver(post_delete, sender=WorkerDocument)
def _delete_worker_document_file(sender, instance, **kwargs):
    if not instance.file:
        return
    if default_storage.exists(instance.file.name):
        instance.file.delete(save=False)
