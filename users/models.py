from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    USER_ROLES = (
        ('worker', '員工/工讀生'),
        ('manager', '店長/管理員'),
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
    primary_store = models.ForeignKey(
        "scheduling.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_workers",
        verbose_name="店別",
    )

    def is_manager(self):
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
    
    def __str__(self):
        return self.display_name()


class WorkerDocument(models.Model):
    CATEGORY_CHOICES = (
        ("id_card_front", "身分證正面"),
        ("id_card_back", "身分證反面"),
        ("driver_license", "駕照"),
        ("bankbook", "存摺"),
    )
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="documents")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to="worker_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile_id}:{self.category}"
