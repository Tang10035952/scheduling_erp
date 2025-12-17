from django.db import models
from users.models import UserProfile # 確保從 users app 匯入

class WorkAvailability(models.Model):
    employee = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    available = models.BooleanField(default=False)  # ← 加上這行！

    class Meta:
        ordering = ["date", "start_time"]

class FillRangeSetting(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.start_date} ~ {self.end_date}"
