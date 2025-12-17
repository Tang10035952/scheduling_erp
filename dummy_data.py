import os
import django
from datetime import date, time, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
from availability.models import WorkAvailability
from scheduling.models import Shift


# -------------------------------
# Step 1：清空資料庫
# -------------------------------
def reset_database():
    print("🧹 Cleaning database...")

    WorkAvailability.objects.all().delete()
    Shift.objects.all().delete()

    UserProfile.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()

    print("✔ Database cleaned.\n")


# -------------------------------
# Step 2：建立店長帳號
# -------------------------------
def create_manager():
    print("👤 Creating manager...")
    manager = User.objects.create_user(
        username="manager",
        password="123456",
        first_name="店長",
        last_name="小王",
    )
    UserProfile.objects.create(
        user=manager,
        role="manager"
    )
    return manager


# -------------------------------
# Step 3：建立員工帳號
# -------------------------------
def create_workers(n=12):
    print(f"👥 Creating {n} workers...")
    workers = []

    for i in range(1, n + 1):
        user = User.objects.create_user(
            username=f"worker{i}",
            password="123456",
            first_name=f"員工{i}",
            last_name="測試"
        )
        profile = UserProfile.objects.create(
            user=user,
            role="worker"
        )
        workers.append(profile)

    return workers


# -------------------------------
# Step 4：建立可上班意願（含 available 欄位）
# -------------------------------

SHIFT_OPTIONS = [
    (time(9, 0), time(13, 0)),   # 早班
    (time(12, 0), time(16, 0)),  # 中班
    (time(17, 0), time(22, 0)),  # 晚班
]

def create_availability(workers):
    print("🗓 Generating availability...")

    today = date.today()

    for worker in workers:
        for d in range(7):  # 一週
            day = today + timedelta(days=d)

            # 70% 機率可上班
            if random.random() < 0.7:
                start, end = random.choice(SHIFT_OPTIONS)

                WorkAvailability.objects.create(
                    employee=worker,
                    date=day,
                    start_time=start,
                    end_time=end,
                    available=True,     # ← 這是關鍵！
                )
            else:
                # 不可上班也要建立紀錄，方便 UI 流程測試
                WorkAvailability.objects.create(
                    employee=worker,
                    date=day,
                    available=False,
                    start_time=None,
                    end_time=None,
                )

    print("✔ Availability generated.\n")


# -------------------------------
# Step 5：依意願自動排班（深色正式班表）
# -------------------------------
def create_shifts(workers):
    print("📅 Creating shifts based on availability...")

    today = date.today()

    for d in range(7):
        day = today + timedelta(days=d)

        # 查當天所有可上班的人
        av_qs = WorkAvailability.objects.filter(date=day, available=True)

        if not av_qs.exists():
            continue

        # 至多排 3 人
        possible = list(av_qs)
        pick_num = min(3, len(possible))

        selected_avs = random.sample(possible, pick_num)

        for av in selected_avs:
            Shift.objects.create(
                employee=av.employee,
                date=day,
                start_time=av.start_time,
                end_time=av.end_time,
                is_published=True,
            )

    print("✔ Shifts created.\n")


# -------------------------------
# 執行流程
# -------------------------------
if __name__ == "__main__":
    reset_database()
    manager = create_manager()
    workers = create_workers(12)
    create_availability(workers)
    create_shifts(workers)

    print("🎉 Dummy data ready!")
    print("👉 Manager 帳號：manager / 123456")
    print("👉 Worker 帳號：worker1 ~ worker12 / 123456")
