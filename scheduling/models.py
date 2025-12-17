from django.db import models
from users.models import UserProfile

class Shift(models.Model):
    employee = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'worker'}, # 限制只能排班給員工
        verbose_name='員工'
    )
    date = models.DateField(verbose_name='日期')
    start_time = models.TimeField(verbose_name='開始時間')
    end_time = models.TimeField(verbose_name='結束時間')
    is_published = models.BooleanField(default=False, verbose_name='是否發佈')

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = "最終排班"
        verbose_name_plural = "最終排班"

    def __str__(self):
        return f"{self.employee.user.get_full_name()} {self.date} ({self.start_time}-{self.end_time})"