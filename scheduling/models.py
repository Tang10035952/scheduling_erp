from django.db import models
from django.db.models import F, Q
from users.models import UserProfile


class Store(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default="#cfe8ff")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SchedulingWindow(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    allow_worker_view = models.BooleanField(default=False)
    allow_worker_edit_shifts = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gte=F("start_date")),
                name="schedulingwindow_end_date_gte_start_date",
            ),
        ]

    def __str__(self):
        return f"{self.start_date} ~ {self.end_date}"


class WorkAvailability(models.Model):
    employee = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "worker"},
        related_name="availabilities",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "員工可上班時段"
        verbose_name_plural = "員工可上班時段"

    def __str__(self):
        return f"{self.employee.display_name()} {self.date} ({self.start_time}-{self.end_time})"


class Shift(models.Model):
    employee = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'worker'}, # 限制只能排班給員工
        verbose_name='員工'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="shifts",
        verbose_name="店別",
        null=True,
        blank=True,
    )
    date = models.DateField(verbose_name='日期')
    start_time = models.TimeField(verbose_name='開始時間')
    end_time = models.TimeField(verbose_name='結束時間')
    is_published = models.BooleanField(default=False, verbose_name='是否發佈')
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="備註")

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = "最終排班"
        verbose_name_plural = "最終排班"

    def __str__(self):
        return f"{self.employee.display_name()} {self.date} ({self.start_time}-{self.end_time})"
