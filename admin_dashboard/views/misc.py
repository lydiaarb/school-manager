"""
views/misc.py — Rooms, Notifications, Registration requests,
                Contact messages, Settings.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import (
    ContactMessage, Formation, Notification,
    RegistrationRequest, Room, SchoolSettings, Student, Employee, TimetableSession, AttendanceRecord, Transaction, Invoice,
)
from .utils import build_excel_response, admin_required
from django.contrib.auth import get_user_model
from .utils import create_and_send_student_activation_code



@admin_required
def statistics_report(request):
    today = timezone.localdate()

    total_students = Student.objects.count()
    total_employees = Employee.objects.count()
    total_formations = Formation.objects.count()
    total_sessions = TimetableSession.objects.filter(is_active=True).count()

    present_count = AttendanceRecord.objects.filter(status="present").count()
    late_count = AttendanceRecord.objects.filter(status="late").count()
    absent_count = AttendanceRecord.objects.filter(status="absent").count()

    total_attendance = present_count + late_count + absent_count
    attendance_rate = round(((present_count + late_count) / total_attendance) * 100) if total_attendance else 0

    total_revenue = Transaction.objects.filter(type="Income").aggregate(total=Sum("amount"))["total"] or 0
    total_expense = Transaction.objects.filter(type="Expense").aggregate(total=Sum("amount"))["total"] or 0
    total_profit = total_revenue - total_expense

    unpaid_invoices = Invoice.objects.filter(status="unpaid").count()
    partial_invoices = Invoice.objects.filter(status="partial").count()
    paid_invoices = Invoice.objects.filter(status="paid").count()
    overdue_invoices = Invoice.objects.filter(status="overdue").count()

    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)

    context = {
        "today": today,
        "school_settings": school_settings,

        "total_students": total_students,
        "total_employees": total_employees,
        "total_formations": total_formations,
        "total_sessions": total_sessions,

        "present_count": present_count,
        "late_count": late_count,
        "absent_count": absent_count,
        "attendance_rate": attendance_rate,

        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "total_profit": total_profit,

        "unpaid_invoices": unpaid_invoices,
        "partial_invoices": partial_invoices,
        "paid_invoices": paid_invoices,
        "overdue_invoices": overdue_invoices,
    }

    return render(request, "admin_dashboard/statistics_report.html", context)

# ══════════════════════════════════════════════════════════════════════════════
#  ROOMS
# ══════════════════════════════════════════════════════════════════════════════


@admin_required
def rooms(request):
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "add_room":
            name = request.POST.get("name", "").strip()
            code = request.POST.get("code", "").strip()
            capacity = request.POST.get("capacity", "").strip()

            if not name:
                messages.error(request, "Le nom de la salle est obligatoire.")
                return redirect("admin_dashboard:rooms")

            Room.objects.create(
                name=name,
                code=code,
                capacity=capacity or 0,
                is_active=request.POST.get("is_active") == "on",
            )
            messages.success(request, "Salle ajoutée avec succès.")
            return redirect("admin_dashboard:rooms")

        elif form_type == "edit_room":
            room_id = request.POST.get("room_id")
            room = get_object_or_404(Room, id=room_id)

            name = request.POST.get("name", "").strip()
            code = request.POST.get("code", "").strip()
            capacity = request.POST.get("capacity", "").strip()

            if not name:
                messages.error(request, "Le nom de la salle est obligatoire.")
                return redirect("admin_dashboard:rooms")

            room.name = name
            room.code = code
            room.capacity = capacity or 0
            room.is_active = request.POST.get("is_active") == "on"
            room.save()

            messages.success(request, "Salle modifiée avec succès.")
            return redirect("admin_dashboard:rooms")

        elif form_type == "delete_room":
            delete_room_id = request.POST.get("delete_room_id")
            room = get_object_or_404(Room, id=delete_room_id)
            room.delete()

            messages.success(request, "Salle supprimée avec succès.")
            return redirect("admin_dashboard:rooms")

    rooms_qs = Room.objects.all().order_by("name")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        rooms_qs = rooms_qs.filter(
            Q(name__icontains=q) | Q(code__icontains=q)
        )

    if status == "active":
        rooms_qs = rooms_qs.filter(is_active=True)
    elif status == "inactive":
        rooms_qs = rooms_qs.filter(is_active=False)

    paginator = Paginator(rooms_qs, 10)
    rooms_page = paginator.get_page(request.GET.get("page"))

    context = {
        "rooms": rooms_page,
        "total_rooms": Room.objects.count(),
        "active_rooms": Room.objects.filter(is_active=True).count(),
        "inactive_rooms": Room.objects.filter(is_active=False).count(),
        "total_capacity": Room.objects.aggregate(total=Sum("capacity"))["total"] or 0,
    }

    return render(request, "admin_dashboard/rooms.html", context)
@admin_required
def export_rooms_excel(request):
    qs     = Room.objects.all().order_by("name")
    q      = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)

    rows = [
        [r.id, r.name, r.code or "", r.capacity, "Active" if r.is_active else "Inactive"]
        for r in qs
    ]

    return build_excel_response(
        title="Salles",
        headers=["ID", "Nom", "Code", "Capacité", "Statut"],
        rows=rows,
        column_widths={"A": 10, "B": 28, "C": 18, "D": 14, "E": 14},
        filename="salles_jouri.xlsx",
    )




# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════


def _apply_notification_filters(qs, request):
    q             = request.GET.get("q", "").strip()
    type_filter   = request.GET.get("type", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(message__icontains=q) |
            Q(related_object__icontains=q)
        )

    if type_filter:
        qs = qs.filter(type=type_filter)

    if status_filter == "unread":
        qs = qs.filter(is_read=False)
    elif status_filter == "read":
        qs = qs.filter(is_read=True)

    return qs

@admin_required
def notifications(request):
    notifications_qs = _apply_notification_filters(
        Notification.objects.all().order_by("-created_at"), request
    )

    paginator          = Paginator(notifications_qs, 10)
    notifications_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(request, "admin_dashboard/notifications.html", {
        "notifications":              notifications_page,
        "total_notifications":        Notification.objects.count(),
        "unread_notifications":       Notification.objects.filter(is_read=False).count(),
        "today_notifications":        Notification.objects.filter(created_at__date=today).count(),
        "high_priority_notifications": Notification.objects.filter(priority="high").count(),
        "notification_types": [
            {"value": v, "label": l} for v, l in Notification.TYPE_CHOICES
        ],
        "query_string": query_params.urlencode(),
    })

@admin_required
def mark_all_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect("admin_dashboard:notifications")

@admin_required
def mark_notification_read(request, id):
    if request.method == "POST":
        notification         = get_object_or_404(Notification, id=id)
        notification.is_read = True
        notification.save()
        messages.success(request, "Notification marquée comme lue.")
    return redirect("admin_dashboard:notifications")

@admin_required
def export_notifications_excel(request):
    qs = _apply_notification_filters(
        Notification.objects.all().order_by("-created_at"), request
    )

    priority_labels = {"low": "Faible", "medium": "Moyenne", "high": "Haute"}
    type_labels     = dict(Notification.TYPE_CHOICES)

    rows = [
        [
            n.id, n.title, n.message,
            type_labels.get(n.type, n.type),
            priority_labels.get(n.priority, n.priority),
            "Lue" if n.is_read else "Non lue",
            n.related_object or "",
            n.created_at.strftime("%d/%m/%Y %H:%M") if n.created_at else "",
        ]
        for n in qs
    ]

    return build_excel_response(
        title="Notifications",
        headers=["ID", "Titre", "Message", "Type", "Priorité",
                 "Statut", "Objet lié", "Date de création"],
        rows=rows,
        column_widths={"A": 10, "B": 30, "C": 55, "D": 18,
                       "E": 16, "F": 14, "G": 24, "H": 22},
        filename="notifications_jouri.xlsx",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRATION REQUESTS
# ══════════════════════════════════════════════════════════════════════════════
@admin_required
def registration_requests(request):
    if request.method == "POST":
        return _handle_registration_post(request)

    requests_qs = RegistrationRequest.objects.select_related("formation").order_by("-created_at")

    q                = request.GET.get("q", "").strip()
    formation_filter = request.GET.get("formation", "").strip()
    status_filter    = request.GET.get("status", "").strip()

    if q:
        requests_qs = requests_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q) |
            Q(message__icontains=q)
        )

    if formation_filter:
        requests_qs = requests_qs.filter(formation_id=formation_filter)

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    paginator     = Paginator(requests_qs, 10)
    requests_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(request, "admin_dashboard/registration_requests.html", {
        "requests":       requests_page,
        "formations":     Formation.objects.all().order_by("title"),
        "pending_count":  RegistrationRequest.objects.filter(status="pending").count(),
        "approved_count": RegistrationRequest.objects.filter(status="approved").count(),
        "rejected_count": RegistrationRequest.objects.filter(status="rejected").count(),
        "query_string":   query_params.urlencode(),
    })

@admin_required
def export_registration_requests_excel(request):
    qs               = RegistrationRequest.objects.select_related("formation").order_by("-created_at")
    q                = request.GET.get("q", "").strip()
    formation_filter = request.GET.get("formation", "").strip()
    status_filter    = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(phone__icontains=q) | Q(email__icontains=q) | Q(message__icontains=q)
        )

    if formation_filter:
        qs = qs.filter(formation_id=formation_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)

    status_labels = {"pending": "En attente", "approved": "Approuvée", "rejected": "Rejetée"}

    rows = [
        [
            r.id, r.first_name, r.last_name, r.phone, r.email or "",
            r.formation.title if r.formation else "",
            r.message or "",
            status_labels.get(r.status, r.status),
            r.created_at.strftime("%d/%m/%Y %H:%M") if r.created_at else "",
        ]
        for r in qs
    ]

    return build_excel_response(
        title="Demandes inscription",
        headers=["ID", "Prénom", "Nom", "Téléphone", "Email",
                 "Formation", "Message", "Statut", "Date de création"],
        rows=rows,
        column_widths={"A": 10, "B": 18, "C": 18, "D": 18, "E": 28,
                       "F": 30, "G": 45, "H": 16, "I": 22},
        filename="demandes_inscription_jouri.xlsx",
    )


def _handle_registration_post(request):
    request_id = request.POST.get("request_id")
    action = request.POST.get("action")
    registration = get_object_or_404(RegistrationRequest, id=request_id)

    if action == "approve":

        UserModel = get_user_model()

        # 🔹 username unique
        base_username = (
            registration.email.split("@")[0]
            if registration.email
            else f"student{registration.id}"
        )

        username = base_username
        counter = 1

        while UserModel.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # 🔹 créer user SANS mot de passe
        user = UserModel.objects.create_user(
            username=username,
            email=registration.email or "",
            password=None,
            first_name=registration.first_name,
            last_name=registration.last_name,
        )

        user.set_unusable_password()
        user.save()

        # 🔹 créer student
        Student.objects.create(
            user=user,
            first_name=registration.first_name,
            last_name=registration.last_name,
            phone=registration.phone,
            formation=registration.formation,
            start_date=timezone.localdate(),
            payment_status="pending",
            is_active=True,
            is_new=True,
        )

        # 🔹 envoyer code
        if registration.email:
            create_and_send_student_activation_code(user, registration.email)

        # 🔹 notifier
        Notification.objects.create(
            title="Inscription approuvée",
            message=(
                f"La demande de {registration.first_name} {registration.last_name} "
                f"pour la formation {registration.formation.title} a été approuvée."
            ),
            type="student",
            priority="medium",
            is_read=False,
            related_object=f"{registration.first_name} {registration.last_name}",
        )

        # 🔹 status
        registration.status = "approved"
        registration.save()

        messages.success(request, f"Étudiant créé + code envoyé à {registration.email}")

    elif action == "reject":
        registration.status = "rejected"
        registration.save()
        messages.success(request, "Demande rejetée avec succès.")

    return redirect("admin_dashboard:registration_requests")


# ══════════════════════════════════════════════════════════════════════════════
#  CONTACT MESSAGES
# ══════════════════════════════════════════════════════════════════════════════
@admin_required
def contact_messages(request):
    messages_qs = ContactMessage.objects.all().order_by("-created_at")

    q = request.GET.get("q", "").strip()
    if q:
        messages_qs = messages_qs.filter(
            Q(name__icontains=q) | Q(email__icontains=q) |
            Q(phone__icontains=q) | Q(message__icontains=q)
        )

    paginator     = Paginator(messages_qs, 10)
    messages_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(request, "admin_dashboard/contact_messages.html", {
        "messages":       messages_page,
        "total_messages": ContactMessage.objects.count(),
        "query_string":   query_params.urlencode(),
    })

@admin_required
def export_contact_messages_excel(request):
    qs = ContactMessage.objects.all().order_by("-created_at")
    q  = request.GET.get("q", "").strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(email__icontains=q) |
            Q(phone__icontains=q) | Q(message__icontains=q)
        )

    rows = [
        [
            m.id, m.name, m.email, m.phone or "", m.message or "",
            m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
        ]
        for m in qs
    ]

    return build_excel_response(
        title="Messages contact",
        headers=["ID", "Nom", "Email", "Téléphone", "Message", "Date"],
        rows=rows,
        column_widths={"A": 10, "B": 24, "C": 30, "D": 18, "E": 60, "F": 22},
        filename="messages_contact_jouri.xlsx",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS  (UI only — backend wiring is a future task)
# ══════════════════════════════════════════════════════════════════════════════
@admin_required
def settings(request):
    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "update_school_identity":
            school_settings.school_name = request.POST.get("school_name", "").strip()
            school_settings.slogan = request.POST.get("slogan", "").strip()
            school_settings.phone = request.POST.get("phone", "").strip()
            school_settings.email = request.POST.get("email", "").strip()
            school_settings.website = request.POST.get("website", "").strip()
            school_settings.address = request.POST.get("address", "").strip()
            school_settings.description = request.POST.get("description", "").strip()
            school_settings.facebook = request.POST.get("facebook", "").strip()
            school_settings.instagram = request.POST.get("instagram", "").strip()

            if request.FILES.get("logo"):
                school_settings.logo = request.FILES["logo"]

            school_settings.save()
            messages.success(request, "Identité de l’école mise à jour avec succès.")
            return redirect("admin_dashboard:settings")

    return render(request, "admin_dashboard/settings.html", {
        "school_settings": school_settings,
        "tabs": [
            {"id": "school",        "label": "Identité de l'école", "icon": "🏫"},
            {"id": "academic",      "label": "Académique",          "icon": "📚"},
            {"id": "financial",     "label": "Financier",           "icon": "💰"},
            {"id": "notifications", "label": "Notifications",       "icon": "🔔"},
            {"id": "appearance",    "label": "Apparence",           "icon": "🎨"},
            {"id": "account",       "label": "Compte",              "icon": "👤"},
            {"id": "system",        "label": "Système",             "icon": "⚙️"},
        ],
        "class_days": ["Sam", "Dim", "Lun", "Mar", "Mer", "Jeu", "Ven"],
        "payment_methods": ["Espèces", "Virement bancaire", "Carte", "Chèque", "Paiement mobile"],
        "notification_settings": [
            {"label": "Nouvelle demande d'inscription", "description": "Notifier lorsqu'un étudiant soumet un formulaire", "default": True},
            {"label": "Paiement reçu", "description": "Notifier lorsqu'un paiement est marqué comme payé", "default": True},
            {"label": "Alerte de faible présence", "description": "Notifier lorsqu'un étudiant passe sous le seuil minimum", "default": True},
            {"label": "Nouvel employé ajouté", "description": "Notifier lorsqu'un nouveau membre du personnel est créé", "default": False},
            {"label": "Formation publiée", "description": "Notifier lorsqu'une formation est publiée sur le site", "default": False},
            {"label": "Rapport hebdomadaire", "description": "Recevoir un résumé hebdomadaire chaque lundi matin", "default": True},
        ],
        "exports": [
            {"label": "Étudiants", "description": "Tous les dossiers des étudiants"},
            {"label": "Employés", "description": "Tous les dossiers du personnel"},
            {"label": "Formations", "description": "Toutes les données des formations"},
            {"label": "Transactions", "description": "Historique financier complet"},
            {"label": "Planning", "description": "Export du planning"},
            {"label": "Sauvegarde complète", "description": "Toutes les données dans un seul fichier"},
        ],
    })