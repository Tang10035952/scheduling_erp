from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    USER_ROLES = (
        ('worker', '員工/工讀生'),
        ('manager', '店長/管理員'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField("名稱", max_length=50, blank=True)
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
    
    def __str__(self):
        return self.display_name()
