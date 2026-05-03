"""
Shared helpers used across multiple views.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from openpyxl import Workbook
from ..models import AttendanceSession, AttendanceRecord, TimetableSession
import secrets
import string
from django.contrib.auth import get_user_model
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from ..models import StudentActivationCode

def generate_temporary_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))
def generate_activation_code():
    return f"{random.randint(100000, 999999)}"
def send_student_activation_email(email, code):
    subject = "Code d’activation - École Jouri"

    message = f"""
Bonjour,

Votre demande d'inscription a été approuvée.

Voici votre code d’activation : {code}

Ce code est valable pendant 15 minutes.

Merci,
École Jouri
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

def create_and_send_student_activation_code(user, email):
    """
    Create a 15-min activation code and send it via email.
    """

    # invalider anciens codes
    StudentActivationCode.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)

    code = generate_activation_code()

    StudentActivationCode.objects.create(
        user=user,
        email=email,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

    send_student_activation_email(email, code)    

def create_teacher_account_for_employee(employee):
    """
    Create a login account only if the employee is a teacher and does not already
    have a linked user account.

    Returns:
        dict | None
        {
            "username": "...",
            "temporary_password": "..."
        }
        or None if no account created.
    """
    if employee.role != "enseignant":
        return None

    if employee.user:
        return None

    UserModel = get_user_model()

    base_username = (
        employee.email.split("@")[0]
        if employee.email
        else f"teacher{employee.id or 'new'}"
    )
    username = base_username
    counter = 1

    while UserModel.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    temp_password = generate_temporary_password()

    user = UserModel.objects.create_user(
        username=username,
        email=employee.email or "",
        password=temp_password,
    )

    employee.user = user
    employee.must_change_password = True
    employee.save(update_fields=["user", "must_change_password"])

    return {
        "username": username,
        "temporary_password": temp_password,
    }

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/site/login/")
        if not request.user.is_staff:
            messages.error(request, "Accès refusé.")
            return redirect("/site/login/")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def logout_view(request):
    logout(request)
    return redirect("/site/login/")


def build_excel_response(title: str, headers: list, rows: list, column_widths: dict, filename: str) -> HttpResponse:
    """
    Build and return an Excel HttpResponse.

    Args:
        title: Worksheet tab name.
        headers: List of column header strings.
        rows: List of lists — one inner list per data row.
        column_widths: Dict mapping column letter to width.
        filename: Download filename including .xlsx extension.
    """
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = title
    worksheet.freeze_panes = "A2"

    worksheet.append(headers)

    for row in rows:
        worksheet.append(row)

    for col, width in column_widths.items():
        worksheet.column_dimensions[col].width = width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    workbook.save(response)
    return response


def update_student_attendance_percentage(student) -> None:
    """
    Recalculate and persist a student's attendance_percentage.
    Called after every check-in and after closing a session.
    """
    total_sessions = AttendanceSession.objects.filter(
        timetable_session__formation=student.formation
    ).count()

    if total_sessions == 0:
        student.attendance_percentage = 0
        student.save(update_fields=["attendance_percentage"])
        return

    present_count = AttendanceRecord.objects.filter(
        student=student,
        attendance_session__timetable_session__formation=student.formation,
        status__in=["present", "late"],
    ).count()

    student.attendance_percentage = round((present_count / total_sessions) * 100)
    student.save(update_fields=["attendance_percentage"])


def check_session_conflicts(teacher_id, room_id, day, start_time, end_time, exclude_id=None):
    """
    Return (teacher_conflict: bool, room_conflict: bool).
    Pass exclude_id when editing an existing session so it is not
    compared against itself.
    """
    base_qs = TimetableSession.objects.filter(
        is_active=True,
        day=day,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )

    if exclude_id:
        base_qs = base_qs.exclude(id=exclude_id)

    teacher_conflict = (
        base_qs.filter(teacher_id=teacher_id).exists()
        if teacher_id else False
    )

    room_conflict = (
        base_qs.filter(room_id=room_id).exists()
        if room_id else False
    )

    return teacher_conflict, room_conflict