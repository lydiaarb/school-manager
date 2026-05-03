from django.db import models
from admin_dashboard.models import Employee

class TeacherSettings(models.Model):
    teacher = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="settings"
    )

    language = models.CharField(max_length=20, default="fr")
    theme = models.CharField(max_length=20, default="dark")
    email_notifications = models.BooleanField(default=True)
    dashboard_compact = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Paramètres - {self.teacher}"
