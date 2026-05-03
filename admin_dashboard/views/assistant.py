from django.shortcuts import render
from django.db.models import Sum

from ..models import (
    Student,
    Employee,
    Formation,
    TimetableSession,
    AttendanceRecord,
    Invoice,
    Transaction,
)
from .utils import admin_required
from ..services.ai_service import ask_ai


def collect_system_data():
    present_count = AttendanceRecord.objects.filter(status="present").count()
    late_count = AttendanceRecord.objects.filter(status="late").count()
    absent_count = AttendanceRecord.objects.filter(status="absent").count()

    total_attendance = present_count + late_count + absent_count
    attendance_rate = round(((present_count + late_count) / total_attendance) * 100) if total_attendance else 0

    total_revenue = Transaction.objects.filter(type="Income").aggregate(total=Sum("amount"))["total"] or 0
    total_expense = Transaction.objects.filter(type="Expense").aggregate(total=Sum("amount"))["total"] or 0

    return {
        "students": Student.objects.count(),
        "employees": Employee.objects.count(),
        "formations": Formation.objects.count(),
        "active_sessions": TimetableSession.objects.filter(is_active=True).count(),

        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "total_profit": total_revenue - total_expense,

        "paid_invoices": Invoice.objects.filter(status="paid").count(),
        "partial_invoices": Invoice.objects.filter(status="partial").count(),
        "unpaid_invoices": Invoice.objects.filter(status="unpaid").count(),
        "overdue_invoices": Invoice.objects.filter(status="overdue").count(),

        "attendance_rate": attendance_rate,
        "present_count": present_count,
        "late_count": late_count,
        "absent_count": absent_count,
    }


@admin_required
def assistant(request):
    response = None
    question = ""

    suggestions = [
        "Donne-moi un résumé global du centre",
        "Analyse la situation financière",
        "Analyse les factures et paiements",
        "Analyse le taux de présence",
        "Que peux-tu dire sur les étudiants ?",
    ]

    if request.method == "POST":
        question = request.POST.get("query", "").strip()

        if not question:
            response = "Veuillez saisir une question."
        else:
            data = collect_system_data()
            response = ask_ai(question, data)

    return render(request, "admin_dashboard/assistant.html", {
        "response": response,
        "question": question,
        "suggestions": suggestions,
    })