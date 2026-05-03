"""
views/employees.py — Employee CRUD, detail page, Excel export.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Employee, Formation
from .utils import (
    build_excel_response,
    admin_required,
    create_teacher_account_for_employee,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_employee_filters(qs, request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(specialty__icontains=q)
        )

    if role:
        qs = qs.filter(role=role)

    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)

    return qs


def _extract_employee_fields(request):
    """Pull and clean employee form fields from POST data."""
    return {
        "first_name": request.POST.get("first_name", "").strip(),
        "last_name": request.POST.get("last_name", "").strip(),
        "phone": request.POST.get("phone", "").strip(),
        "email": request.POST.get("email", "").strip(),
        "role": request.POST.get("role", "").strip(),
        "specialty": request.POST.get("specialty", "").strip(),
        "experience_years": request.POST.get("experience_years", "").strip() or 0,
        "formation_id": request.POST.get("formation", "").strip() or None,
        "is_active": request.POST.get("is_active") == "on",
    }


# ── Views ─────────────────────────────────────────────────────────────────────

@admin_required
def employees(request):
    if request.method == "POST":
        return _handle_employee_post(request)

    employees_qs = _apply_employee_filters(
        Employee.objects.select_related("formation", "user").order_by("-id"),
        request,
    )

    paginator = Paginator(employees_qs, 10)
    employees_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "admin_dashboard/employees.html",
        {
            "employees": employees_page,
            "formations": Formation.objects.all().order_by("title"),
            "roles": Employee.ROLE_CHOICES,
            "total_employees": Employee.objects.count(),
            "active_employees": Employee.objects.filter(is_active=True).count(),
            "inactive_employees": Employee.objects.filter(is_active=False).count(),
            "total_trainers": Employee.objects.filter(role="enseignant").count(),
            "query_string": query_params.urlencode(),
        },
    )


@admin_required
def employee_detail(request, employee_id):
    employee = get_object_or_404(
        Employee.objects.select_related("formation", "user"),
        id=employee_id,
    )
    return render(
        request,
        "admin_dashboard/employee_detail.html",
        {"employee": employee},
    )


@admin_required
def export_employees_excel(request):
    qs = _apply_employee_filters(
        Employee.objects.select_related("formation").order_by("-id"),
        request,
    )
    role_labels = dict(Employee.ROLE_CHOICES)

    rows = [
        [
            e.id,
            e.first_name,
            e.last_name,
            e.phone or "",
            e.email or "",
            role_labels.get(e.role, e.role),
            e.specialty or "",
            e.experience_years,
            e.formation.title if e.formation else "",
            "Actif" if e.is_active else "Inactif",
        ]
        for e in qs
    ]

    return build_excel_response(
        title="Employés",
        headers=[
            "ID",
            "Prénom",
            "Nom",
            "Téléphone",
            "Email",
            "Rôle",
            "Spécialité",
            "Expérience",
            "Formation",
            "Statut",
        ],
        rows=rows,
        column_widths={
            "A": 10,
            "B": 18,
            "C": 18,
            "D": 18,
            "E": 28,
            "F": 18,
            "G": 24,
            "H": 14,
            "I": 28,
            "J": 14,
        },
        filename="employes_jouri.xlsx",
    )


# ── POST handler ──────────────────────────────────────────────────────────────

def _handle_employee_post(request):
    form_type = request.POST.get("form_type")

    if form_type == "add_employee":
        fields = _extract_employee_fields(request)

        if not fields["first_name"] or not fields["last_name"]:
            messages.error(request, "Le prénom et le nom sont obligatoires.")
            return redirect("admin_dashboard:employees")

        employee = Employee.objects.create(**fields)

        account_data = create_teacher_account_for_employee(employee)

        if account_data:
            messages.success(
                request,
                "Enseignant ajouté avec succès. "
                f"Identifiant : {account_data['username']} | "
                f"Mot de passe temporaire : {account_data['temporary_password']}"
            )
        else:
            messages.success(request, "Employé ajouté avec succès.")

    elif form_type == "edit_employee":
        employee_id = request.POST.get("employee_id")
        employee = get_object_or_404(Employee, id=employee_id)
        fields = _extract_employee_fields(request)

        if not fields["first_name"] or not fields["last_name"]:
            messages.error(request, "Le prénom et le nom sont obligatoires.")
            return redirect("admin_dashboard:employees")

        for attr, value in fields.items():
            setattr(employee, attr, value)
        employee.save()

        account_data = create_teacher_account_for_employee(employee)

        if account_data:
            messages.success(
                request,
                "Employé modifié avec succès. "
                f"Compte enseignant créé : {account_data['username']} | "
                f"Mot de passe temporaire : {account_data['temporary_password']}"
            )
        else:
            messages.success(request, "Employé modifié avec succès.")

    elif form_type == "delete_employee":
        employee = get_object_or_404(
            Employee,
            id=request.POST.get("delete_employee_id"),
        )
        employee.delete()
        messages.success(request, "Employé supprimé avec succès.")

    return redirect("admin_dashboard:employees")