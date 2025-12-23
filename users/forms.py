from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class WorkerCreationForm(UserCreationForm):
    name = forms.CharField(label="名稱", max_length=50)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

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
