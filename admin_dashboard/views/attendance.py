"""
views/attendance.py — Attendance sessions, check-in, close, export.
"""

from datetime import datetime, timedelta
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import AttendanceRecord, AttendanceSession, Student, TimetableSession
from .utils import update_student_attendance_percentage, admin_required


@admin_required
def attendance_sessions(request):
    """List all attendance sessions with record counts."""
    sessions_qs = AttendanceSession.objects.select_related(
        "timetable_session",
        "timetable_session__formation",
    ).order_by("-date", "-id")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        sessions_qs = sessions_qs.filter(
            Q(timetable_session__title__icontains=q) |
            Q(timetable_session__formation__title__icontains=q)
        )

    if status == "open":
        sessions_qs = sessions_qs.filter(is_open=True)
    elif status == "closed":
        sessions_qs = sessions_qs.filter(is_open=False)

    paginator = Paginator(sessions_qs, 10)
    sessions_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    sessions_data = [
        {
            "id": s.id,
            "title": s.timetable_session.title,
            "formation": s.timetable_session.formation.title if s.timetable_session.formation else "—",
            "date": s.date,
            "count": s.records.count(),
            "is_open": s.is_open,
        }
        for s in sessions_page
    ]

    context = {
        "sessions": sessions_data,
        "sessions_page": sessions_page,
        "total_sessions": AttendanceSession.objects.count(),
        "open_sessions": AttendanceSession.objects.filter(is_open=True).count(),
        "closed_sessions": AttendanceSession.objects.filter(is_open=False).count(),
        "total_records": AttendanceRecord.objects.count(),
        "query_string": query_string,
    }

    return render(request, "admin_dashboard/attendance_sessions.html", context)

@admin_required
def open_attendance(request, session_id):
    """Open (or re-open) an attendance session for today."""
    timetable_session = get_object_or_404(TimetableSession, id=session_id)
    today             = timezone.localdate()

    attendance_session, created = AttendanceSession.objects.get_or_create(
        timetable_session=timetable_session,
        date=today,
        defaults={"is_open": True},
    )

    if created:
        messages.success(request, f"Présence ouverte pour {timetable_session.title} ({today}).")
    elif attendance_session.is_open:
        messages.info(request, f"La présence est déjà ouverte pour {timetable_session.title}.")
    else:
        attendance_session.is_open = True
        attendance_session.save()
        messages.success(request, f"Présence rouverte pour {timetable_session.title} ({today}).")

    return redirect("admin_dashboard:attendance_checkin", attendance_session_id=attendance_session.id)

@admin_required
def attendance_checkin(request, attendance_session_id):
    """QR scan / token check-in page."""
    attendance_session = get_object_or_404(
        AttendanceSession.objects.select_related(
            "timetable_session",
            "timetable_session__formation",
            "timetable_session__teacher",
            "timetable_session__room",
        ),
        id=attendance_session_id,
    )

    timetable_session = attendance_session.timetable_session
    scanned_records   = attendance_session.records.select_related("student").order_by("-scanned_at")

    if request.method == "POST":
        return _process_checkin(request, attendance_session, timetable_session)

    return render(request, "admin_dashboard/attendance_checkin.html", {
        "attendance_session": attendance_session,
        "timetable_session":  timetable_session,
        "records":            scanned_records,
        "records_count":      scanned_records.count(),
    })

@admin_required
def close_attendance(request, attendance_session_id):
    """Close (or re-open) an attendance session and mark absentees."""
    attendance_session = get_object_or_404(AttendanceSession, id=attendance_session_id)

    if request.method == "POST":
        if attendance_session.is_open:
            _mark_absentees_and_close(attendance_session)
            messages.success(request, "Présence clôturée avec succès.")
        else:
            attendance_session.is_open = True
            attendance_session.save()
            messages.success(request, "Présence rouverte avec succès.")

    return redirect("admin_dashboard:attendance_checkin", attendance_session_id=attendance_session.id)

@admin_required
def export_attendance_excel(request, attendance_session_id):
    """Export a single attendance session to Excel."""
    session = get_object_or_404(AttendanceSession, id=attendance_session_id)
    records = session.records.select_related("student")

    wb = Workbook()
    ws = wb.active
    ws.title        = "Présence"
    ws.freeze_panes = "A2"

    ws.append(["Nom de l'étudiant", "Code étudiant", "Statut", "Heure de scan"])

    for record in records:
        ws.append([
            f"{record.student.first_name} {record.student.last_name}",
            record.student.student_code,
            record.status,
            record.scanned_at.strftime("%Y-%m-%d %H:%M"),
        ])

    for col, width in {"A": 30, "B": 16, "C": 14, "D": 20}.items():
        ws.column_dimensions[col].width = width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="presence_{session.id}.xlsx"'
    wb.save(response)
    return response


# ── Private helpers ───────────────────────────────────────────────────────────

def _process_checkin(request, attendance_session, timetable_session):
    redirect_kwargs = {"attendance_session_id": attendance_session.id}

    if not attendance_session.is_open:
        messages.error(request, "La présence est clôturée. Aucun pointage supplémentaire autorisé.")
        return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)

    qr_token = request.POST.get("qr_token", "").strip()

    if not qr_token:
        messages.error(request, "Veuillez scanner ou saisir un token QR.")
        return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)

    try:
        student = Student.objects.select_related("formation").get(qr_token=qr_token)
    except Student.DoesNotExist:
        messages.error(request, "QR code invalide. Étudiant introuvable.")
        return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)

    if not student.is_active:
        messages.error(request, f"{student.first_name} {student.last_name} est inactif(ve).")
        return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)

    if student.formation_id != timetable_session.formation_id:
        messages.error(
            request,
            f"{student.first_name} {student.last_name} n'appartient pas à "
            f"la formation {timetable_session.formation.title}.",
        )
        return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)

    if AttendanceRecord.objects.filter(
        attendance_session=attendance_session, student=student
    ).exists():
        messages.warning(
            request,
            f"{student.first_name} {student.last_name} est déjà pointé(e).",
        )
        return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)

    # Determine present vs late
    now           = timezone.localtime()
    session_start = timezone.make_aware(
        datetime.combine(attendance_session.date, timetable_session.start_time)
    )
    status = "late" if now > session_start + timedelta(minutes=10) else "present"

    AttendanceRecord.objects.create(
        attendance_session=attendance_session,
        student=student,
        status=status,
    )
    update_student_attendance_percentage(student)

    label = " (En retard)" if status == "late" else ""
    messages.success(
        request,
        f"{student.first_name} {student.last_name} pointé(e) avec succès{label}.",
    )
    return redirect("admin_dashboard:attendance_checkin", **redirect_kwargs)


def _mark_absentees_and_close(attendance_session):
    """Mark all students not yet checked in as absent, then close the session."""
    attendance_session.is_open = False
    attendance_session.save()

    formation_students   = Student.objects.filter(
        formation=attendance_session.timetable_session.formation
    )
    checked_student_ids  = AttendanceRecord.objects.filter(
        attendance_session=attendance_session
    ).values_list("student_id", flat=True)

    absent_records = [
        AttendanceRecord(
            attendance_session=attendance_session,
            student=student,
            status="absent",
        )
        for student in formation_students
        if student.id not in checked_student_ids
    ]

    # Bulk create is more efficient than individual creates
    AttendanceRecord.objects.bulk_create(absent_records)

    for student in formation_students:
        update_student_attendance_percentage(student)