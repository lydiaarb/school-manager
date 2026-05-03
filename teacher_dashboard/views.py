from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import TeacherProfileForm, TeacherSettingsForm
from .models import TeacherSettings



from admin_dashboard.models import TimetableSession, Notification
from .decorators import teacher_required
from admin_dashboard.models import (
    TimetableSession,
    Notification,
    AttendanceSession,
    AttendanceRecord,
    Student,
)
@login_required
@teacher_required
def attendance_checkin(request, session_id):
    teacher = request.user.employee_profile

    timetable_session = get_object_or_404(
        TimetableSession.objects.select_related("formation", "room", "teacher"),
        id=session_id,
        teacher=teacher,
        is_active=True,
    )

    attendance_session, created = AttendanceSession.objects.get_or_create(
        timetable_session=timetable_session,
        date=now().date(),
        defaults={"is_open": True},
    )

    if request.method == "POST":
        if not attendance_session.is_open:
            messages.error(request, "La séance de présence est fermée.")
            return redirect("teacher_dashboard:attendance_checkin", session_id=timetable_session.id)

        qr_token = request.POST.get("qr_token", "").strip()

        if not qr_token:
            messages.error(request, "Veuillez scanner ou saisir un QR code.")
            return redirect("teacher_dashboard:attendance_checkin", session_id=timetable_session.id)

        student = Student.objects.filter(qr_code=qr_token).first()

        if not student:
            student = Student.objects.filter(student_code=qr_token).first()

        if not student:
            messages.error(request, "QR code invalide. Étudiant introuvable.")
            return redirect("teacher_dashboard:attendance_checkin", session_id=timetable_session.id)

        if timetable_session.formation and student.formation != timetable_session.formation:
            messages.error(request, "Cet étudiant n'appartient pas à cette formation.")
            return redirect("teacher_dashboard:attendance_checkin", session_id=timetable_session.id)

        record, record_created = AttendanceRecord.objects.get_or_create(
            attendance_session=attendance_session,
            student=student,
            defaults={
                "status": "present",
                "scanned_at": now(),
            },
        )

        if record_created:
            messages.success(request, f"{student.first_name} {student.last_name} marqué présent.")
        else:
            messages.warning(request, "Cet étudiant est déjà enregistré pour cette séance.")

        return redirect("teacher_dashboard:attendance_checkin", session_id=timetable_session.id)

    records = AttendanceRecord.objects.filter(
        attendance_session=attendance_session
    ).select_related("student").order_by("-scanned_at")

    context = {
        "teacher": teacher,
        "timetable_session": timetable_session,
        "attendance_session": attendance_session,
        "records": records,
        "records_count": records.count(),
    }

    return render(request, "teacher_dashboard/attendance_checkin.html", context)


@login_required
@teacher_required
def close_attendance(request, attendance_id):
    attendance = get_object_or_404(
        AttendanceSession,
        id=attendance_id,
        timetable_session__teacher=request.user.employee_profile,
    )

    attendance.is_open = not attendance.is_open
    attendance.save(update_fields=["is_open"])

    if attendance.is_open:
        messages.success(request, "La présence a été rouverte.")
    else:
        messages.success(request, "La présence a été clôturée.")

    return redirect(
        "teacher_dashboard:attendance_checkin",
        session_id=attendance.timetable_session.id,
    )

@login_required
@teacher_required
def home(request):
    teacher = request.user.employee_profile

    today_name = now().strftime("%A").lower()
    sessions_today = TimetableSession.objects.filter(
        teacher=teacher,
        is_active=True,
        day=today_name
    ).select_related("formation", "room").order_by("start_time")

    upcoming_sessions = TimetableSession.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related("formation", "room").order_by("day", "start_time")[:5]

    notifications = Notification.objects.order_by("-created_at")[:5]

    context = {
        "teacher": teacher,
        "sessions_today": sessions_today,
        "upcoming_sessions": upcoming_sessions,
        "notifications": notifications,
    }
    return render(request, "teacher_dashboard/home.html", context)

@login_required
@teacher_required
def timetable(request):
    teacher = request.user.employee_profile

    days = [
        {"value": "saturday", "label": "Samedi"},
        {"value": "sunday", "label": "Dimanche"},
        {"value": "monday", "label": "Lundi"},
        {"value": "tuesday", "label": "Mardi"},
        {"value": "wednesday", "label": "Mercredi"},
        {"value": "thursday", "label": "Jeudi"},
        {"value": "friday", "label": "Vendredi"},
        
    ]

    sessions = TimetableSession.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related("formation", "room").order_by("day", "start_time")

    selected_day = request.GET.get("day")
    if selected_day:
        sessions = sessions.filter(day=selected_day)

    context = {
        "teacher": teacher,
        "sessions": sessions,
        "days": days,
        "total_sessions": sessions.count(),
    }

    return render(request, "teacher_dashboard/timetable.html", context)

@login_required
@teacher_required
def notifications(request):
    teacher = request.user.employee_profile

    notifications_qs = Notification.objects.filter(
    recipient=request.user
).order_by("-created_at")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        notifications_qs = notifications_qs.filter(
            Q(title__icontains=q) | Q(message__icontains=q)
        )

    if status == "unread":
        notifications_qs = notifications_qs.filter(is_read=False)
    elif status == "read":
        notifications_qs = notifications_qs.filter(is_read=True)

    total_notifications = notifications_qs.count()
    unread_notifications = notifications_qs.filter(is_read=False).count()
    today_notifications = notifications_qs.filter(created_at__date=now().date()).count()

    paginator = Paginator(notifications_qs, 8)
    page_number = request.GET.get("page")
    notifications_page = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    context = {
        "teacher": teacher,
        "notifications": notifications_page,
        "total_notifications": total_notifications,
        "unread_notifications": unread_notifications,
        "today_notifications": today_notifications,
        "query_string": query_string,
    }

    return render(request, "teacher_dashboard/notifications.html", context)


@login_required
@teacher_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    messages.success(request, "Notification marquée comme lue.")
    return redirect("teacher_dashboard:notifications")


@login_required
@teacher_required
def mark_all_notifications_read(request):
    Notification.objects.filter(is_read=False).update(is_read=True)

    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect("teacher_dashboard:notifications")



@login_required
@teacher_required
def settings_view(request):
    teacher = request.user.employee_profile
    settings_obj, created = TeacherSettings.objects.get_or_create(teacher=teacher)

    profile_form = TeacherProfileForm(instance=teacher)
    settings_form = TeacherSettingsForm(instance=settings_obj)
    password_form = PasswordChangeForm(request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            profile_form = TeacherProfileForm(request.POST, instance=teacher)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil mis à jour avec succès.")
                return redirect("teacher_dashboard:change_password")

        elif form_type == "settings":
            settings_form = TeacherSettingsForm(request.POST, instance=settings_obj)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Préférences mises à jour avec succès.")
                return redirect("teacher_dashboard:change_password")

        elif form_type == "password":
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                teacher.must_change_password = False
                teacher.save(update_fields=["must_change_password"])
                messages.success(request, "Mot de passe modifié avec succès.")
                return redirect("teacher_dashboard:change_password")

    return render(request, "teacher_dashboard/change_password.html", {
        "teacher": teacher,
        "profile_form": profile_form,
        "settings_form": settings_form,
        "password_form": password_form,
    })


@login_required
@teacher_required
def teacher_logout(request):
    logout(request)
    return redirect("/site/login/")