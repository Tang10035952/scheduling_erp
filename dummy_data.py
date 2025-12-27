import os
import django
from datetime import date, time, timedelta
import random
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ.setdefault('DB_NAME', 'staging_db')
os.environ.setdefault('DB_USER', 'staging_user')
os.environ.setdefault('DB_PASSWORD', 'staging_pw')
os.environ.setdefault('DB_HOST', '35.221.202.58')
os.environ.setdefault('DB_PORT', '3307')
django.setup()

from django.contrib.auth.models import User
from django.db import connection
from django.core.files.base import ContentFile
from users.models import UserProfile, WorkerDocument
from scheduling.models import Shift, SchedulingWindow, WorkAvailability, Store


# -------------------------------
# Step 1：清空資料庫
# -------------------------------
def reset_database():
    print("🧹 Cleaning database...")

    WorkAvailability.objects.all().delete()
    Shift.objects.all().delete()
    SchedulingWindow.objects.all().delete()
    Store.objects.all().delete()
    WorkerDocument.objects.all().delete()

    UserProfile.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()

    print("✔ Database cleaned.\n")


def drop_legacy_profile_columns():
    print("🧩 Checking legacy userprofile columns...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users_userprofile'")
            if not cursor.fetchone():
                print("ℹ users_userprofile table missing, skip.")
                return
            cursor.execute("SHOW COLUMNS FROM users_userprofile LIKE 'registered_by_email'")
            if cursor.fetchone():
                cursor.execute("ALTER TABLE users_userprofile DROP COLUMN registered_by_email")
                print("✔ Dropped registered_by_email column.")
            else:
                print("ℹ registered_by_email column not found, skip.")
    except Exception as err:
        print(f"⚠ Failed to adjust legacy schema: {err}")


# -------------------------------
# Step 2：建立店長帳號
# -------------------------------
def create_manager():
    print("👤 Creating manager...")
    manager = User.objects.create_user(
        username="manager",
        password="123456",
        first_name="",
        last_name="",
    )
    UserProfile.objects.create(
        user=manager,
        role="manager",
        name="店長 李強",
    )
    return manager


# -------------------------------
# Step 3：建立員工帳號
# -------------------------------
FAKE_WORKERS = [
    ("陳志明", "陳志明"),
    ("林美玲", "林美玲"),
    ("張建宏", "張建宏"),
    ("王雅雯", "王雅雯"),
    ("李冠宇", "李冠宇"),
    ("黃心怡", "黃心怡"),
    ("吳宇軒", "吳宇軒"),
    ("周佳穎", "周佳穎"),
]

EDUCATION_CHOICES = ["高中在學", "高中畢業", "大學在學", "大學畢業", "其他"]
MARITAL_CHOICES = ["單身", "已婚"]
GENDER_CHOICES = ["男", "女"]


def random_id_number():
    prefix = random.choice(string.ascii_uppercase)
    return prefix + "".join(random.choices(string.digits, k=9))


def random_phone():
    return "".join(random.choices(string.digits, k=10))


def random_birthday():
    today = date.today()
    years = random.randint(18, 35)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return date(today.year - years, month, day)


def attach_documents(profile):
    def make_file(name):
        return ContentFile(b"dummy file", name=name)

    WorkerDocument.objects.create(
        profile=profile,
        category="id_card_front",
        file=make_file(f"{profile.user.username}_id_front.txt"),
    )
    WorkerDocument.objects.create(
        profile=profile,
        category="id_card_back",
        file=make_file(f"{profile.user.username}_id_back.txt"),
    )
    WorkerDocument.objects.create(
        profile=profile,
        category="driver_license",
        file=make_file(f"{profile.user.username}_driver.txt"),
    )
    WorkerDocument.objects.create(
        profile=profile,
        category="bankbook",
        file=make_file(f"{profile.user.username}_bankbook.txt"),
    )

def create_workers(stores):
    print(f"👥 Creating {len(FAKE_WORKERS)} workers...")
    workers = []

    for i, (display_name, real_name) in enumerate(FAKE_WORKERS, start=1):
        education = random.choice(EDUCATION_CHOICES)
        education_other = "補充說明" if education == "其他" else ""
        user = User.objects.create_user(
            username=f"worker{i}",
            password="123456",
            first_name="",
            last_name="",
        )
        profile = UserProfile.objects.create(
            user=user,
            role="worker",
            name=display_name,
            real_name=real_name,
            gender=random.choice(GENDER_CHOICES),
            birthday=random_birthday(),
            id_number=random_id_number(),
            marital_status=random.choice(MARITAL_CHOICES),
            education=education,
            education_other=education_other,
            contact_address=f"台北市中山區中山北路 {i} 段 {i} 號",
            registered_address="同通訊地址",
            mobile_phone=random_phone(),
            emergency_contact_name="王小明",
            emergency_contact_relation="家人",
            emergency_contact_phone=random_phone(),
            work_experience="飲料店 / 2022-2023 / 個人規劃",
            primary_store=random.choice(stores),
        )
        attach_documents(profile)
        workers.append(profile)

    return workers


def create_stores():
    print("🏬 Creating stores...")
    stores = [
        Store.objects.create(name="林森店", color="#cfe8ff"),
        Store.objects.create(name="中正店", color="#ffe4c4"),
    ]
    return stores


SHIFT_OPTIONS = [
    (time(9, 0), time(13, 0)),   # 早班
    (time(12, 0), time(16, 0)),  # 中班
    (time(17, 0), time(22, 0)),  # 晚班
]
BREAK_RULES = [
    {"min_hours": 4, "break_minutes": 30},
    {"min_hours": 8, "break_minutes": 60},
]
SHIFT_NOTES = [
    "",
    "",
    "交接提醒",
    "注意補貨",
    "新人協助",
    "客訴跟進",
    "盤點支援",
    "臨時調班",
]


# -------------------------------
# Step 5：依意願自動排班（深色正式班表）
# -------------------------------
def calculate_break_minutes(start_time, end_time):
    start_min = start_time.hour * 60 + start_time.minute
    end_min = end_time.hour * 60 + end_time.minute
    if end_min <= start_min:
        end_min += 24 * 60
    duration = end_min - start_min
    applied = 0
    for rule in BREAK_RULES:
        if duration > int(rule["min_hours"] * 60):
            applied = max(applied, rule["break_minutes"])
    return applied


def create_shifts(workers, stores):
    print("📅 Creating shifts...")

    today = date.today()
    month_start = today.replace(day=1)
    last_day = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    total_days = last_day.day

    for d in range(total_days):
        day = month_start + timedelta(days=d)

        for worker in workers:
            if random.random() < 0.45:
                continue

            shift_count = 2 if random.random() < 0.2 else 1
            chosen = random.sample(SHIFT_OPTIONS, k=shift_count)

            for start, end in chosen:
                store = None if random.random() < 0.25 else random.choice(stores)
                break_minutes = calculate_break_minutes(start, end)
                Shift.objects.create(
                    employee=worker,
                    store=store,
                    date=day,
                    start_time=start,
                    end_time=end,
                    break_minutes=break_minutes,
                    is_published=True,
                    note=random.choice(SHIFT_NOTES),
                )

    print("✔ Shifts created.\n")


def create_window_and_availability(workers):
    print("📝 Creating scheduling window and availability...")
    today = date.today()
    month_start = today.replace(day=1)
    last_day = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    SchedulingWindow.objects.create(
        start_date=month_start,
        end_date=last_day,
        allow_worker_view=True,
        allow_worker_edit_shifts=True,
        allow_worker_register=True,
        break_rules=BREAK_RULES,
    )

    target_date = date(today.year, today.month, 16)
    for worker in workers:
        if worker.name == "陳志明":
            WorkAvailability.objects.create(
                employee=worker,
                date=target_date,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
            continue
        if random.random() < 0.6:
            continue
        start, end = random.choice(SHIFT_OPTIONS)
        WorkAvailability.objects.create(
            employee=worker,
            date=month_start + timedelta(days=random.randint(0, last_day.day - 1)),
            start_time=start,
            end_time=end,
        )

    print("✔ Window and availability created.\n")


# -------------------------------
# 執行流程
# -------------------------------
if __name__ == "__main__":
    drop_legacy_profile_columns()
    reset_database()
    manager = create_manager()
    stores = create_stores()
    workers = create_workers(stores)
    create_shifts(workers, stores)
    create_window_and_availability(workers)

    print("🎉 Dummy data ready!")
    print("👉 Manager 帳號：manager / 123456")
    print("👉 Worker 帳號：worker1 ~ worker8 / 123456")
