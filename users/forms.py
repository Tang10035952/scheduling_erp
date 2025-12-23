import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


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
