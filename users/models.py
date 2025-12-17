from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    USER_ROLES = (
        ('worker', '員工/工讀生'),
        ('manager', '店長/管理員'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='worker')

    def is_manager(self):
        return self.role == 'manager'
    
    def __str__(self):
        return self.user.username