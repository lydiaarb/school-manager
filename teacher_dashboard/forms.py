from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from admin_dashboard.models import Employee
from .models import TeacherSettings

class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["first_name", "last_name", "phone", "email", "specialty"]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900"
            }),
            "last_name": forms.TextInput(attrs={
                "class": "w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900"
            }),
            "phone": forms.TextInput(attrs={
                "class": "w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900"
            }),
            "specialty": forms.TextInput(attrs={
                "class": "w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-slate-900"
            }),
        }


class TeacherSettingsForm(forms.ModelForm):
    class Meta:
        model = TeacherSettings
        fields = ["language", "theme", "email_notifications", "dashboard_compact"]
        widgets = {
            "language": forms.Select(
                choices=[("fr", "Français"), ("en", "Anglais")],
                attrs={"class": "w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white"}
            ),
            "theme": forms.Select(
                choices=[("dark", "Sombre"), ("light", "Clair")],
                attrs={"class": "w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-white"}
            ),
            "email_notifications": forms.CheckboxInput(attrs={"class": "h-5 w-5 rounded border-white/20 bg-white/10"}),
            "dashboard_compact": forms.CheckboxInput(attrs={"class": "h-5 w-5 rounded border-white/20 bg-white/10"}),
        }