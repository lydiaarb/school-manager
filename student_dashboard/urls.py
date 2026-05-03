from django.urls import path
from . import views

app_name = "student_dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("timetable/", views.timetable, name="timetable"),
    path("attendance/", views.attendance, name="attendance"),
    path("payments/", views.payments, name="payments"),

    path("logout/", views.student_logout, name="logout"),
    path("notifications/", views.notifications, name="notifications"),
path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
path("qr-code/", views.student_qr_code, name="student_qr_code"),
]