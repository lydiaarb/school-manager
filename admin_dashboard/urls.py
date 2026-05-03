from django.urls import path
from . import views

app_name = "admin_dashboard"

urlpatterns = [
    path("", views.admin_dashboard, name="admin_dashboard"),
    path("logout/", views.logout_view, name="logout"),

    path("students/", views.students, name="students"),
    path("students/<int:student_id>/", views.student_detail, name="student_detail"),
    path("students/<int:student_id>/qr/", views.student_qr_code, name="student_qr_code"),
    path("students/export/excel/", views.export_students_excel, name="export_students_excel"),

    path("employees/", views.employees, name="employees"),
    path("employees/export/excel/", views.export_employees_excel, name="export_employees_excel"),
    path("employees/<int:employee_id>/", views.employee_detail, name="employee_detail"),

    path("formations/", views.formations, name="formations"),
    path("formations/export/excel/", views.export_formations_excel, name="export_formations_excel"),

    path("timetable/", views.timetable, name="timetable"),
    path("timetable/export/excel/", views.export_timetable_excel, name="export_timetable_excel"),

    path("rooms/", views.rooms, name="rooms"),
    path("rooms/export/excel/", views.export_rooms_excel, name="export_rooms_excel"),

    path("registration_requests/", views.registration_requests, name="registration_requests"),
    path("registration_requests/export/excel/", views.export_registration_requests_excel, name="export_registration_requests_excel"),

    path("notifications/", views.notifications, name="notifications"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("notifications/<int:id>/mark-read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/export/excel/", views.export_notifications_excel, name="export_notifications_excel"),

    path("finance/", views.finance, name="finance"),
    path("finance/export/excel/", views.export_finance_excel, name="export_finance_excel"),

    path("contact-messages/", views.contact_messages, name="contact_messages"),
    path("contact-messages/export/excel/", views.export_contact_messages_excel, name="export_contact_messages_excel"),

    path("attendance/open/<int:session_id>/", views.open_attendance, name="open_attendance"),
    path("attendance/checkin/<int:attendance_session_id>/", views.attendance_checkin, name="attendance_checkin"),
    path("attendance/<int:attendance_session_id>/close/", views.close_attendance, name="close_attendance"),
    path("attendance/sessions/", views.attendance_sessions, name="attendance_sessions"),
    path("attendance/export/<int:attendance_session_id>/", views.export_attendance_excel, name="export_attendance_excel"),

    path("settings/", views.settings, name="settings"),
    path("users/", views.users, name="users"),
    path("statistics-report/", views.statistics_report, name="statistics_report"),
    path("assistant/", views.assistant, name="assistant"),
    path("create-admin/", create_admin),
]