from django.urls import path
from . import views

app_name = "teacher_dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("timetable/", views.timetable, name="timetable"),
    
    path("change-password/", views.settings_view, name="change_password"),
    path("logout/", views.teacher_logout, name="logout"),
 path("attendance/<int:session_id>/", views.attendance_checkin, name="attendance_checkin"),
path("attendance/<int:attendance_id>/close/", views.close_attendance, name="close_attendance"),
path("notifications/", views.notifications, name="notifications"),
path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    
]