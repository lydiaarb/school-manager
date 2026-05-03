from secrets import token_urlsafe

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render

from .utils import admin_required


User = get_user_model()


def _get_account_role(user):
    if user.is_superuser or user.is_staff:
        return "admin", "Administrateur"

    if hasattr(user, "student_profile"):
        return "student", "Étudiant"

    if hasattr(user, "employee_profile"):
        employee = user.employee_profile
        if employee.role == "enseignant":
            return "teacher", "Enseignant"
        return "employee", employee.get_role_display()

    return "unknown", "Non lié"


def _get_linked_profile(user):
    if hasattr(user, "student_profile"):
        student = user.student_profile
        return student, f"{student.first_name} {student.last_name}", "student"

    if hasattr(user, "employee_profile"):
        employee = user.employee_profile
        return employee, f"{employee.first_name} {employee.last_name}", "employee"

    return None, "Aucun profil lié", "none"


def _apply_user_filters(qs, request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(student_profile__first_name__icontains=q)
            | Q(student_profile__last_name__icontains=q)
            | Q(employee_profile__first_name__icontains=q)
            | Q(employee_profile__last_name__icontains=q)
            | Q(employee_profile__email__icontains=q)
        ).distinct()

    if role == "admin":
        qs = qs.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif role == "student":
        qs = qs.filter(student_profile__isnull=False)
    elif role == "teacher":
        qs = qs.filter(employee_profile__role="enseignant")
    elif role == "employee":
        qs = qs.filter(employee_profile__isnull=False).exclude(employee_profile__role="enseignant")
    elif role == "unlinked":
        qs = qs.filter(student_profile__isnull=True, employee_profile__isnull=True, is_staff=False, is_superuser=False)

    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)

    return qs


@admin_required
def users(request):
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        try:
            account = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "Compte introuvable.")
            return redirect("admin_dashboard:users")

        if action == "toggle_status":
            if account.id == request.user.id:
                messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
                return redirect("admin_dashboard:users")

            account.is_active = not account.is_active
            account.save(update_fields=["is_active"])

            if account.is_active:
                messages.success(request, "Compte activé avec succès.")
            else:
                messages.success(request, "Compte désactivé avec succès.")

        elif action == "reset_password":
            temporary_password = token_urlsafe(8)
            account.set_password(temporary_password)
            account.save(update_fields=["password"])

            messages.success(
                request,
                f"Mot de passe réinitialisé pour {account.username}. "
                f"Nouveau mot de passe temporaire : {temporary_password}"
            )

        return redirect("admin_dashboard:users")

    users_qs = _apply_user_filters(
        User.objects.select_related("student_profile", "employee_profile").order_by("-date_joined"),
        request,
    )

    paginator = Paginator(users_qs, 10)
    users_page = paginator.get_page(request.GET.get("page"))

    for account in users_page:
        account.account_role, account.account_role_label = _get_account_role(account)
        account.linked_profile, account.linked_profile_name, account.linked_profile_type = _get_linked_profile(account)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(request, "admin_dashboard/users.html", {
        "users": users_page,
        "query_string": query_params.urlencode(),

        "total_accounts": User.objects.count(),
        "active_accounts": User.objects.filter(is_active=True).count(),
        "inactive_accounts": User.objects.filter(is_active=False).count(),
        "student_accounts": User.objects.filter(student_profile__isnull=False).count(),
        "teacher_accounts": User.objects.filter(employee_profile__role="enseignant").count(),
        "admin_accounts": User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count(),
    })