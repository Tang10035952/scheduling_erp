import os
import re
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import UserProfile


IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def _is_allowed_image_upload(file_obj):
    content_type = (file_obj.content_type or "").lower()
    if content_type in IMAGE_CONTENT_TYPES:
        return True
    if content_type in {"application/octet-stream", ""}:
        name = (file_obj.name or "").lower()
        return os.path.splitext(name)[1] in IMAGE_EXTENSIONS
    return False


def _is_allowed_upload(file_obj, allow_pdf=False):
    if _is_allowed_image_upload(file_obj):
        return True
    if allow_pdf and (file_obj.content_type or "").lower() == "application/pdf":
        return True
    return False


class TempPasswordResetForm(forms.Form):
    username = forms.CharField(label="帳號", max_length=150)
    temp_password = forms.CharField(label="臨時密碼", widget=forms.PasswordInput)
    new_password1 = forms.CharField(label="新密碼", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="再次確認新密碼", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get("username") or "").strip()
        temp_password = (cleaned.get("temp_password") or "").strip()
        new_password1 = (cleaned.get("new_password1") or "").strip()
        new_password2 = (cleaned.get("new_password2") or "").strip()

        if username and temp_password:
            user = authenticate(username=username, password=temp_password)
            if not user:
                raise forms.ValidationError("帳號或臨時密碼錯誤。")
            self.user = user

        if new_password1 and new_password2 and new_password1 != new_password2:
            self.add_error("new_password2", "兩次輸入的密碼不一致。")

        if new_password1:
            try:
                validate_password(new_password1, user=self.user)
            except ValidationError as exc:
                self.add_error("new_password1", exc)

        cleaned["username"] = username
        cleaned["temp_password"] = temp_password
        cleaned["new_password1"] = new_password1
        cleaned["new_password2"] = new_password2
        return cleaned


class WorkerCreationForm(UserCreationForm):
    username = forms.CharField(label="帳號", min_length=6, max_length=150)
    name = forms.CharField(label="名稱", max_length=50)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.setdefault("placeholder", "帳號至少6碼")
        self.fields["name"].widget.attrs.setdefault("placeholder", "名稱中文5字或英文10字內，可中英混合")
        self.fields["password1"].widget.attrs.setdefault("placeholder", "至少6碼，可純數字或英文字")
        self.fields["password2"].widget.attrs.setdefault("placeholder", "再次輸入密碼")

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if re.search(r"\s", username):
            raise forms.ValidationError("帳號不可包含空白。")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("帳號已被使用。")
        return username

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            return name
        if re.search(r"\s", name):
            raise forms.ValidationError("名稱不可包含空白。")
        if UserProfile.objects.filter(name=name).exists():
            raise forms.ValidationError("名稱已被使用。")
        if not re.fullmatch(r"[A-Za-z\u4e00-\u9fff]+", name):
            raise forms.ValidationError("名稱僅允許中英文。")
        weighted_length = 0
        for ch in name:
            if "\u4e00" <= ch <= "\u9fff":
                weighted_length += 2
            else:
                weighted_length += 1
        if weighted_length > 10:
            raise forms.ValidationError("名稱英文最多10字、中文最多5字，混合請等比例縮減。")
        return name

    def clean_password1(self):
        password = (self.cleaned_data.get("password1") or "").strip()
        if re.search(r"\s", password):
            raise forms.ValidationError("密碼不可包含空白。")
        return password

    def clean_password2(self):
        password = (self.cleaned_data.get("password2") or "").strip()
        if re.search(r"\s", password):
            raise forms.ValidationError("密碼不可包含空白。")
        self.cleaned_data["password2"] = password
        return super().clean_password2()

    def save(self, commit=True):
        """Persist as a regular employee account (no staff/admin flags)."""
        user = super().save(commit=False)
        user.is_staff = False
        user.is_superuser = False
        user.first_name = ""
        user.last_name = ""
        if commit:
            user.save()
        return user


GENDER_CHOICES = [("男", "男"), ("女", "女")]
MARITAL_CHOICES = [("單身", "單身"), ("已婚", "已婚")]
EDUCATION_CHOICES = [
    ("高中在學", "高中在學"),
    ("高中畢業", "高中畢業"),
    ("大學在學", "大學在學"),
    ("大學畢業", "大學畢業"),
    ("其他", "其他"),
]




class ManagerWorkerCreateForm(UserCreationForm):
    username = forms.CharField(label="帳號", min_length=6, max_length=150)
    display_name = forms.CharField(label="名稱", max_length=50)
    real_name = forms.CharField(label="真實姓名", max_length=50)
    gender = forms.ChoiceField(label="性別", choices=GENDER_CHOICES)
    birthday = forms.DateField(
        label="生日",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    id_number = forms.CharField(label="身分證字號", max_length=10)
    marital_status = forms.ChoiceField(label="婚姻狀況", choices=MARITAL_CHOICES)
    education = forms.ChoiceField(label="學歷", choices=EDUCATION_CHOICES)
    education_other = forms.CharField(label="學歷補充說明", required=False, max_length=10)
    contact_address = forms.CharField(label="通訊地址", max_length=255)
    registered_address = forms.CharField(label="戶籍地址", max_length=255)
    mobile_phone = forms.CharField(label="手機電話", max_length=10)
    emergency_contact_name = forms.CharField(label="緊急聯絡人姓名", max_length=10)
    emergency_contact_relation = forms.CharField(label="緊急聯絡人關係", max_length=10)
    emergency_contact_phone = forms.CharField(label="緊急聯絡人電話", max_length=10)
    work_experience = forms.CharField(
        label="工作經歷",
        max_length=50,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 50}),
    )
    id_card_front = forms.FileField(label="身分證正面", required=False)
    id_card_back = forms.FileField(label="身分證反面", required=False)
    driver_license_file = forms.FileField(label="駕照", required=False)
    bankbook_file = forms.FileField(label="存摺影本", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.setdefault("placeholder", "至少6碼，可純數字或英文字")
        self.fields["password2"].widget.attrs.setdefault("placeholder", "再次輸入密碼")

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("帳號已被使用。")
        return username

    def clean_id_number(self):
        value = (self.cleaned_data.get("id_number") or "").strip()
        if not re.fullmatch(r"[A-Z][0-9]{9}", value):
            raise forms.ValidationError("身分證字號格式不正確。")
        return value

    def clean_mobile_phone(self):
        value = (self.cleaned_data.get("mobile_phone") or "").strip()
        if not re.fullmatch(r"[0-9]{10}", value):
            raise forms.ValidationError("手機電話格式不正確，需為 10 碼數字。")
        return value

    def clean_emergency_contact_phone(self):
        value = (self.cleaned_data.get("emergency_contact_phone") or "").strip()
        if not re.fullmatch(r"[0-9]{10}", value):
            raise forms.ValidationError("緊急聯絡人電話需為 10 碼數字。")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("education") == "其他" and not cleaned.get("education_other"):
            self.add_error("education_other", "請補充學歷說明。")

        if self.is_bound:
            for field_name in ("id_card_front", "id_card_back"):
                if not self.files.get(field_name):
                    self.add_error(field_name, "請上傳身分證正反面。")
        for field_name in ("id_card_front", "id_card_back"):
            file_obj = self.files.get(field_name)
            if not file_obj:
                continue
            if not _is_allowed_image_upload(file_obj):
                self.add_error(field_name, "身分證檔案需為 JPG/PNG/HEIC。")
            if file_obj.size > 10 * 1024 * 1024:
                self.add_error(field_name, "檔案大小不可超過 10MB。")
        for field_name in ("driver_license_file", "bankbook_file"):
            file_obj = self.files.get(field_name)
            if not file_obj:
                continue
            if not _is_allowed_upload(file_obj, allow_pdf=True):
                self.add_error(field_name, "檔案格式需為 JPG/PNG/HEIC/PDF。")
            if file_obj.size > 10 * 1024 * 1024:
                self.add_error(field_name, "檔案大小不可超過 10MB。")

        return cleaned


class ManagerWorkerUpdateForm(forms.Form):
    display_name = forms.CharField(label="名稱", max_length=50)
    real_name = forms.CharField(label="真實姓名", max_length=50)
    gender = forms.ChoiceField(label="性別", choices=GENDER_CHOICES)
    birthday = forms.DateField(
        label="生日",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    id_number = forms.CharField(label="身分證字號", max_length=10)
    marital_status = forms.ChoiceField(label="婚姻狀況", choices=MARITAL_CHOICES)
    education = forms.ChoiceField(label="學歷", choices=EDUCATION_CHOICES)
    education_other = forms.CharField(label="學歷補充說明", required=False, max_length=10)
    contact_address = forms.CharField(label="通訊地址", max_length=255)
    registered_address = forms.CharField(label="戶籍地址", max_length=255)
    mobile_phone = forms.CharField(label="手機電話", max_length=10)
    emergency_contact_name = forms.CharField(label="緊急聯絡人姓名", max_length=10)
    emergency_contact_relation = forms.CharField(label="緊急聯絡人關係", max_length=10)
    emergency_contact_phone = forms.CharField(label="緊急聯絡人電話", max_length=10)
    work_experience = forms.CharField(
        label="工作經歷",
        max_length=50,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 50}),
    )
    id_card_front = forms.FileField(label="身分證正面", required=False)
    id_card_back = forms.FileField(label="身分證反面", required=False)
    driver_license_file = forms.FileField(label="駕照", required=False)
    bankbook_file = forms.FileField(label="存摺影本", required=False)

    def clean_id_number(self):
        value = (self.cleaned_data.get("id_number") or "").strip()
        if not re.fullmatch(r"[A-Z][0-9]{9}", value):
            raise forms.ValidationError("身分證字號格式不正確。")
        return value

    def clean_mobile_phone(self):
        value = (self.cleaned_data.get("mobile_phone") or "").strip()
        if not re.fullmatch(r"[0-9]{10}", value):
            raise forms.ValidationError("手機電話格式不正確，需為 10 碼數字。")
        return value

    def clean_emergency_contact_phone(self):
        value = (self.cleaned_data.get("emergency_contact_phone") or "").strip()
        if not re.fullmatch(r"[0-9]{10}", value):
            raise forms.ValidationError("緊急聯絡人電話需為 10 碼數字。")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("education") == "其他" and not cleaned.get("education_other"):
            self.add_error("education_other", "請補充學歷說明。")

        if self.is_bound:
            for field_name in ("driver_license_file", "bankbook_file"):
                if not self.files.get(field_name):
                    self.add_error(field_name, "請上傳必要附件。")
        for field_name in ("driver_license_file", "bankbook_file"):
            file_obj = self.files.get(field_name)
            if not file_obj:
                continue
            if not _is_allowed_upload(file_obj, allow_pdf=True):
                self.add_error(field_name, "檔案格式需為 JPG/PNG/HEIC/PDF。")
            if file_obj.size > 10 * 1024 * 1024:
                self.add_error(field_name, "檔案大小不可超過 10MB。")

        for field_name in ("id_card_front", "id_card_back"):
            file_obj = self.files.get(field_name)
            if not file_obj:
                continue
            if not _is_allowed_image_upload(file_obj):
                self.add_error(field_name, "身分證檔案需為 JPG/PNG/HEIC。")
            if file_obj.size > 10 * 1024 * 1024:
                self.add_error(field_name, "檔案大小不可超過 10MB。")
        return cleaned
