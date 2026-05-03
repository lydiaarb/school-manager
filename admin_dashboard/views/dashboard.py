"""
views/dashboard.py — Admin home dashboard.
"""

from django.shortcuts import render
from django.db.models import Sum

from ..models import (
    Student, Employee, TimetableSession, Transaction,
    RegistrationRequest, Formation, AttendanceRecord,
)
from .utils import admin_required

@admin_required
def admin_dashboard(request):
    # ── Attendance totals ──────────────────────────────────────────────────────
    total_records = AttendanceRecord.objects.count()
    present_count = AttendanceRecord.objects.filter(status="present").count()
    late_count    = AttendanceRecord.objects.filter(status="late").count()
    absent_count  = AttendanceRecord.objects.filter(status="absent").count()

    attendance_rate = (
        round(((present_count + late_count) / total_records) * 100)
        if total_records > 0 else 0
    )

    # ── Best formation by attendance ───────────────────────────────────────────
    best_formation = None
    best_rate      = 0

    for formation in Formation.objects.all():
        formation_records = AttendanceRecord.objects.filter(
            attendance_session__timetable_session__formation=formation
        )
        formation_total = formation_records.count()

        if formation_total == 0:
            continue

        formation_present = formation_records.filter(status__in=["present", "late"]).count()
        formation_rate    = (formation_present / formation_total) * 100

        if formation_rate > best_rate:
            best_rate      = formation_rate
            best_formation = formation

    return render(request, "admin_dashboard/adminhome.html", {
        # Core stats
        "total_students":   Student.objects.count(),
        "total_employees":  Employee.objects.count(),
        "total_sessions":   TimetableSession.objects.filter(is_active=True).count(),
        "total_revenue":    Transaction.objects.filter(type="Income").aggregate(Sum("amount"))["amount__sum"] or 0,
        "pending_requests": RegistrationRequest.objects.filter(status="pending").count(),
        "recent_students":      Student.objects.order_by("-created_at")[:5],
        "recent_transactions":  Transaction.objects.order_by("-created_at")[:5],
        # Attendance stats
        "attendance_rate":  attendance_rate,
        "present_count":    present_count,
        "late_count":       late_count,
        "absent_count":     absent_count,
        "best_formation":   best_formation,
        "best_rate":        round(best_rate),
    })