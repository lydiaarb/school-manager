"""
views/timetable.py — Timetable CRUD and Excel export.
"""

from datetime import datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import Employee, Formation, Room, TimetableSession
from .utils import (
    build_excel_response,
    check_session_conflicts,
    suggest_available_slots,
    admin_required,
)


DAYS = [
    {"value": "saturday", "label": "Samedi"},
    {"value": "sunday", "label": "Dimanche"},
    {"value": "monday", "label": "Lundi"},
    {"value": "tuesday", "label": "Mardi"},
    {"value": "wednesday", "label": "Mercredi"},
    {"value": "thursday", "label": "Jeudi"},
    {"value": "friday", "label": "Vendredi"},
]

DAY_LABELS_FR = {d["value"]: d["label"] for d in DAYS}

COLOR_LABELS = {
    "blue": "Cours de cuisine",
    "emerald": "Cours de pâtisserie",
    "violet": "Cours de boulangerie",
    "amber": "Séances de démonstration",
    "rose": "Ateliers desserts",
    "cyan": "Séances pratiques",
    "slate": "Sessions générales",
}


def _store_form_state(request, modal_name, data):
    request.session["timetable_modal"] = modal_name
    request.session["timetable_form_data"] = data


def _pop_form_state(request):
    modal_name = request.session.pop("timetable_modal", "")
    form_data = request.session.pop("timetable_form_data", {})
    return modal_name, form_data


def _build_redirect_url(request):
    params = []

    for key in ("current_formation", "current_teacher", "current_day"):
        value = request.POST.get(key, "").strip()
        param_name = key.replace("current_", "")

        if value:
            params.append(f"{param_name}={value}")

    base = reverse("admin_dashboard:timetable")
    return f"{base}?{'&'.join(params)}" if params else base


def _extract_session_fields(request):
    return {
        "title": request.POST.get("title", "").strip(),
        "formation_id": request.POST.get("formation", "").strip(),
        "teacher_id": request.POST.get("teacher", "").strip(),
        "day": request.POST.get("day", "").strip(),
        "start_time_raw": request.POST.get("start_time", "").strip(),
        "end_time_raw": request.POST.get("end_time", "").strip(),
        "room_id": request.POST.get("room", "").strip(),
        "color": request.POST.get("color", "slate").strip() or "slate",
    }


def _validate_and_parse_times(fields, modal, request):
    if not all([
        fields["title"],
        fields["day"],
        fields["start_time_raw"],
        fields["end_time_raw"],
    ]):
        _store_form_state(request, modal, fields)
        messages.error(request, "Veuillez remplir les champs obligatoires de la session.")
        return None, None

    if not fields["formation_id"]:
        _store_form_state(request, modal, fields)
        messages.error(request, "Veuillez sélectionner une formation.")
        return None, None

    try:
        start_time = datetime.strptime(fields["start_time_raw"], "%H:%M").time()
        end_time = datetime.strptime(fields["end_time_raw"], "%H:%M").time()
    except ValueError:
        _store_form_state(request, modal, fields)
        messages.error(request, "Le format des horaires est invalide.")
        return None, None

    if start_time >= end_time:
        _store_form_state(request, modal, fields)
        messages.error(request, "L'heure de début doit être antérieure à l'heure de fin.")
        return None, None

    return start_time, end_time


def _get_duration_minutes(start_time, end_time):
    return (
        datetime.combine(datetime.today(), end_time)
        - datetime.combine(datetime.today(), start_time)
    ).seconds // 60


def _build_conflict_message(teacher_conflict, room_conflict, suggestions):
    conflict_types = []

    if teacher_conflict:
        conflict_types.append("formateur")

    if room_conflict:
        conflict_types.append("salle")

    if suggestions:
        suggestions_text = " | ".join(suggestions)
        return (
            f"Conflit détecté ({', '.join(conflict_types)}). "
            f"Créneaux disponibles sans conflit : {suggestions_text}."
        )

    return (
        f"Conflit détecté ({', '.join(conflict_types)}). "
        "Aucun créneau disponible trouvé pour cette durée."
    )


def _handle_add_session(request):
    fields = _extract_session_fields(request)
    form_data = {**fields}
    redirect_url = _build_redirect_url(request)

    start_time, end_time = _validate_and_parse_times(fields, "add", request)

    if start_time is None:
        return redirect(redirect_url)

    teacher_conflict, room_conflict = check_session_conflicts(
        fields["teacher_id"],
        fields["room_id"],
        fields["day"],
        start_time,
        end_time,
    )

    duration_minutes = _get_duration_minutes(start_time, end_time)

    suggestions = suggest_available_slots(
        fields["teacher_id"],
        fields["room_id"],
        fields["day"],
        duration_minutes,
    )

    if teacher_conflict or room_conflict:
        request.session.pop("timetable_modal", None)
        request.session.pop("timetable_form_data", None)

    messages.error(
        request,
        _build_conflict_message(teacher_conflict, room_conflict, suggestions),
    )
    return redirect(redirect_url)

    TimetableSession.objects.create(
        title=fields["title"],
        formation_id=fields["formation_id"],
        teacher_id=fields["teacher_id"] or None,
        day=fields["day"],
        start_time=start_time,
        end_time=end_time,
        room_id=fields["room_id"] or None,
        color=fields["color"],
        is_active=True,
    )

    messages.success(request, "Session ajoutée avec succès.")
    return redirect(redirect_url)


def _handle_edit_session(request):
    session_id = request.POST.get("session_id")
    session = get_object_or_404(TimetableSession, id=session_id)

    fields = _extract_session_fields(request)
    form_data = {"session_id": session_id, **fields}
    redirect_url = _build_redirect_url(request)

    start_time, end_time = _validate_and_parse_times(fields, "edit", request)

    if start_time is None:
        return redirect(redirect_url)

    teacher_conflict, room_conflict = check_session_conflicts(
        fields["teacher_id"],
        fields["room_id"],
        fields["day"],
        start_time,
        end_time,
        exclude_id=session.id,
    )

    duration_minutes = _get_duration_minutes(start_time, end_time)

    suggestions = suggest_available_slots(
        fields["teacher_id"],
        fields["room_id"],
        fields["day"],
        duration_minutes,
        exclude_id=session.id,
    )

    if teacher_conflict or room_conflict:
        request.session.pop("timetable_modal", None)
        request.session.pop("timetable_form_data", None)

    messages.error(
        request,
        _build_conflict_message(teacher_conflict, room_conflict, suggestions),
    )
    return redirect(redirect_url)

    session.title = fields["title"]
    session.formation_id = fields["formation_id"]
    session.teacher_id = fields["teacher_id"] or None
    session.day = fields["day"]
    session.start_time = start_time
    session.end_time = end_time
    session.room_id = fields["room_id"] or None
    session.color = fields["color"]
    session.save()

    messages.success(request, "Session modifiée avec succès.")
    return redirect(redirect_url)


def _handle_delete_session(request):
    session = get_object_or_404(
        TimetableSession,
        id=request.POST.get("delete_session_id"),
    )

    session.delete()
    messages.success(request, "Session supprimée avec succès.")
    return redirect(_build_redirect_url(request))


def _build_timetable_grid(sessions_qs):
    time_slots = list(
        sessions_qs.order_by("start_time", "end_time")
        .values("start_time", "end_time")
        .distinct()
    )

    rows = []

    for slot in time_slots:
        row = {
            "label": f"{slot['start_time'].strftime('%H:%M')} - {slot['end_time'].strftime('%H:%M')}",
            "cells": [],
        }

        for day in DAYS:
            slot_sessions = sessions_qs.filter(
                day=day["value"],
                start_time=slot["start_time"],
                end_time=slot["end_time"],
            )

            session_items = []

            for s in slot_sessions:
                teacher_conflict, room_conflict = check_session_conflicts(
                    s.teacher_id,
                    s.room_id,
                    s.day,
                    s.start_time,
                    s.end_time,
                    exclude_id=s.id,
                )

                has_conflict = teacher_conflict or room_conflict
                suggestions = []

                if has_conflict:
                    duration_minutes = _get_duration_minutes(s.start_time, s.end_time)

                    suggestions = suggest_available_slots(
                        s.teacher_id,
                        s.room_id,
                        s.day,
                        duration_minutes,
                        exclude_id=s.id,
                    )

                session_items.append({
                    "id": s.id,
                    "title": s.title,
                    "teacher": str(s.teacher) if s.teacher else "Aucun formateur",
                    "teacher_id": s.teacher_id or "",
                    "room": s.room.name if s.room else "Aucune salle",
                    "room_id": s.room_id or "",
                    "formation": s.formation.title if s.formation else "",
                    "formation_id": s.formation_id or "",
                    "day": s.day,
                    "start_time": s.start_time.strftime("%H:%M"),
                    "end_time": s.end_time.strftime("%H:%M"),
                    "color": s.color or "slate",
                    "teacher_conflict": teacher_conflict,
                    "room_conflict": room_conflict,
                    "has_conflict": has_conflict,
                    "suggestions": suggestions,
                })

            row["cells"].append({
                "day": day["value"],
                "sessions": session_items,
            })

        rows.append(row)

    return rows


@admin_required
def timetable(request):
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        handlers = {
            "add_session": _handle_add_session,
            "edit_session": _handle_edit_session,
            "delete_session": _handle_delete_session,
        }

        handler = handlers.get(form_type)

        if handler:
            return handler(request)

    sessions_qs = TimetableSession.objects.select_related(
        "formation",
        "teacher",
        "room",
    ).filter(is_active=True)

    formation_id = request.GET.get("formation", "").strip()
    teacher_id = request.GET.get("teacher", "").strip()
    day_filter = request.GET.get("day", "").strip()

    if formation_id:
        sessions_qs = sessions_qs.filter(formation_id=formation_id)

    if teacher_id:
        sessions_qs = sessions_qs.filter(teacher_id=teacher_id)

    if day_filter:
        sessions_qs = sessions_qs.filter(day=day_filter)

    reopen_modal, modal_form_data = _pop_form_state(request)

    upcoming_sessions = [
        {
            "title": s.title,
            "day": s.get_day_display(),
            "time": s.time_label,
            "teacher": str(s.teacher) if s.teacher else "Aucun formateur",
            "room": s.room.name if s.room else "Aucune salle",
            "color": s.color or "slate",
        }
        for s in sessions_qs.order_by("day", "start_time")[:5]
    ]

    legend = [
        {"color": color, "label": COLOR_LABELS.get(color, "Session")}
        for color in sessions_qs.values_list("color", flat=True).distinct()
    ]

    return render(request, "admin_dashboard/timetable.html", {
        "days": DAYS,
        "timetable": _build_timetable_grid(sessions_qs),
        "formations": Formation.objects.all().order_by("title"),
        "teachers": Employee.objects.filter(is_active=True).order_by("first_name", "last_name"),
        "rooms": Room.objects.filter(is_active=True).order_by("name"),
        "upcoming_sessions": upcoming_sessions,
        "legend": legend,
        "total_sessions": sessions_qs.count(),
        "active_formations": sessions_qs.values("formation").distinct().count(),
        "scheduled_teachers": sessions_qs.exclude(teacher__isnull=True).values("teacher").distinct().count(),
        "used_rooms": sessions_qs.exclude(room__isnull=True).values("room").distinct().count(),
        "reopen_modal": reopen_modal,
        "modal_form_data": modal_form_data,
    })


@admin_required
def export_timetable_excel(request):
    sessions_qs = TimetableSession.objects.select_related(
        "formation",
        "teacher",
        "room",
    ).filter(is_active=True)

    for key, attr in [
        ("formation", "formation_id"),
        ("teacher", "teacher_id"),
        ("day", "day"),
    ]:
        value = request.GET.get(key, "").strip()

        if value:
            sessions_qs = sessions_qs.filter(**{attr: value})

    sessions_qs = sessions_qs.order_by("day", "start_time", "end_time", "title")

    rows = []

    for s in sessions_qs:
        teacher_conflict, room_conflict = check_session_conflicts(
            s.teacher_id,
            s.room_id,
            s.day,
            s.start_time,
            s.end_time,
            exclude_id=s.id,
        )

        rows.append([
            s.title,
            s.formation.title if s.formation else "",
            str(s.teacher) if s.teacher else "Aucun formateur",
            s.room.name if s.room else "Aucune salle",
            DAY_LABELS_FR.get(s.day, s.day),
            s.start_time.strftime("%H:%M") if s.start_time else "",
            s.end_time.strftime("%H:%M") if s.end_time else "",
            s.color or "slate",
            "Oui" if teacher_conflict else "Non",
            "Oui" if room_conflict else "Non",
            "Oui" if (teacher_conflict or room_conflict) else "Non",
        ])

    return build_excel_response(
        title="Planning",
        headers=[
            "Titre",
            "Formation",
            "Formateur",
            "Salle",
            "Jour",
            "Heure début",
            "Heure fin",
            "Couleur",
            "Conflit formateur",
            "Conflit salle",
            "Conflit global",
        ],
        rows=rows,
        column_widths={
            "A": 30,
            "B": 28,
            "C": 28,
            "D": 20,
            "E": 14,
            "F": 14,
            "G": 14,
            "H": 14,
            "I": 18,
            "J": 16,
            "K": 16,
        },
        filename="planning_jouri.xlsx",
    )