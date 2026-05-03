"""
views/students.py — Student CRUD, detail page, QR code, Excel export.
"""

from io import BytesIO

import qrcode
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..models import AttendanceRecord, Formation, Student
from .utils import build_excel_response, admin_required





PAYMENT_LABELS = {
    "paid":    "Payé",
    "partial": "Partiel",
    "pending": "En attente",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _apply_student_filters(qs, request):
    q                = request.GET.get("q", "").strip()
    formation_filter = request.GET.get("formation", "").strip()
    payment_status   = request.GET.get("payment_status", "").strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(phone__icontains=q)
        )

    if formation_filter:
        qs = qs.filter(formation_id=formation_filter)

    if payment_status:
        qs = qs.filter(payment_status=payment_status)

    return qs


# ── Views ─────────────────────────────────────────────────────────────────────
@admin_required
def students(request):
    if request.method == "POST":
        return _handle_student_post(request)

    students_qs = _apply_student_filters(
        Student.objects.select_related("formation").order_by("-id"), request
    )

    paginator     = Paginator(students_qs, 10)
    students_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(request, "admin_dashboard/students.html", {
        "students":        students_page,
        "formations":      Formation.objects.all().order_by("title"),
        "total_students":  Student.objects.count(),
        "active_students": Student.objects.filter(is_active=True).count(),
        "new_students":    Student.objects.filter(is_new=True).count(),
        "pending_payments": Student.objects.filter(payment_status="pending").count(),
        "query_string":    query_params.urlencode(),
    })

@admin_required
def student_detail(request, student_id):
    student = get_object_or_404(Student.objects.select_related("formation"), id=student_id)

    attendance_records = (
        AttendanceRecord.objects
        .filter(student=student)
        .select_related("attendance_session", "attendance_session__timetable_session")
        .order_by("-attendance_session__date", "-scanned_at")
    )

    return render(request, "admin_dashboard/student_detail.html", {
        "student":            student,
        "attendance_records": attendance_records,
        "present_count":      attendance_records.filter(status="present").count(),
        "late_count":         attendance_records.filter(status="late").count(),
        "absent_count":       attendance_records.filter(status="absent").count(),
        "total_sessions":     attendance_records.count(),
    })

@admin_required
def student_qr_code(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    try:
        qr = qrcode.make(student.qr_token)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)
        return HttpResponse(buffer.getvalue(), content_type="image/png")
    except Exception:
        messages.error(request, "Erreur lors de la génération du QR code.")
        return redirect("admin_dashboard:student_detail", student_id=student.id)

@admin_required
def export_students_excel(request):
    qs   = _apply_student_filters(
        Student.objects.select_related("formation").order_by("-id"), request
    )
    rows = [
        [
            s.id,
            s.first_name,
            s.last_name,
            s.phone,
            s.formation.title if s.formation else "",
            s.start_date.strftime("%d/%m/%Y") if s.start_date else "",
            PAYMENT_LABELS.get(s.payment_status, s.payment_status),
            s.attendance_percentage,
            "Oui" if s.is_active else "Non",
            "Oui" if s.is_new else "Non",
        ]
        for s in qs
    ]

    return build_excel_response(
        title="Étudiants",
        headers=["ID", "Prénom", "Nom", "Téléphone", "Formation", "Date de début",
                 "Statut paiement", "Présence (%)", "Actif", "Nouveau"],
        rows=rows,
        column_widths={"A": 10, "B": 18, "C": 18, "D": 18, "E": 30,
                       "F": 16, "G": 18, "H": 14, "I": 12, "J": 12},
        filename="etudiants_jouri.xlsx",
    )


# ── POST handler ──────────────────────────────────────────────────────────────

def _handle_student_post(request):
    delete_student_id = request.POST.get("delete_student_id")
    student_id        = request.POST.get("student_id")

    if delete_student_id:
        get_object_or_404(Student, id=delete_student_id).delete()
        messages.success(request, "Étudiant supprimé avec succès.")
        return redirect("admin_dashboard:students")

    first_name     = request.POST.get("first_name", "").strip()
    last_name      = request.POST.get("last_name", "").strip()
    phone          = request.POST.get("phone", "").strip()
    formation_id   = request.POST.get("formation", "").strip()
    start_date     = request.POST.get("start_date", "").strip()
    payment_status = request.POST.get("payment_status", "pending").strip() or "pending"
    is_active      = request.POST.get("is_active") == "on"
    is_new         = request.POST.get("is_new") == "on"

    if not all([first_name, last_name, phone, formation_id, start_date]):
        messages.error(request, "Veuillez remplir tous les champs obligatoires.")
        return redirect("admin_dashboard:students")

    if student_id:
        student                = get_object_or_404(Student, id=student_id)
        student.first_name     = first_name
        student.last_name      = last_name
        student.phone          = phone
        student.formation_id   = formation_id
        student.start_date     = start_date
        student.payment_status = payment_status
        student.is_active      = is_active
        student.is_new         = is_new
        student.save()
        messages.success(request, "Étudiant modifié avec succès.")
    else:
        Student.objects.create(
            first_name=first_name, last_name=last_name,
            phone=phone, formation_id=formation_id,
            start_date=start_date, payment_status=payment_status,
            is_active=is_active, is_new=is_new,
        )
        messages.success(request, "Étudiant ajouté avec succès.")

    return redirect("admin_dashboard:students")