"""
views/formations.py — Formation CRUD + Excel export.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import Formation
from .utils import build_excel_response, admin_required





# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_formation_filters(qs, request):
    q               = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()
    status_filter   = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(short_description__icontains=q) |
            Q(category__icontains=q) |
            Q(chef_name__icontains=q)
        )

    if category_filter:
        qs = qs.filter(category__iexact=category_filter)

    if status_filter == "published":
        qs = qs.filter(is_published=True)
    elif status_filter == "draft":
        qs = qs.filter(is_published=False)

    return qs


# ── Views ─────────────────────────────────────────────────────────────────────
@admin_required
def formations(request):
    if request.method == "POST":
        return _handle_formation_post(request)

    formations_qs = _apply_formation_filters(
        Formation.objects.all().order_by("-created_at"), request
    )

    paginator       = Paginator(formations_qs, 10)
    formations_page = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    categories = (
        Formation.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    return render(request, "admin_dashboard/formations.html", {
        "formations":      formations_page,
        "published_count": Formation.objects.filter(is_published=True).count(),
        "draft_count":     Formation.objects.filter(is_published=False).count(),
        "chefs_count":     Formation.objects.exclude(chef_name="").values("chef_name").distinct().count(),
        "categories":      categories,
        "query_string":    query_params.urlencode(),
    })

@admin_required
def export_formations_excel(request):
    qs   = _apply_formation_filters(Formation.objects.all().order_by("-created_at"), request)
    rows = [
        [
            f.id,
            f.title,
            f.short_description or "",
            f.description or "",
            f.category or "",
            f.chef_name or "",
            f.duration or "",
            str(f.price) if f.price is not None else "",
            "Publiée" if f.is_published else "Brouillon",
            f.created_at.strftime("%d/%m/%Y %H:%M") if f.created_at else "",
        ]
        for f in qs
    ]

    return build_excel_response(
        title="Formations",
        headers=["ID", "Titre", "Description courte", "Description", "Catégorie",
                 "Chef formateur", "Durée", "Prix (DZD)", "Statut", "Date de création"],
        rows=rows,
        column_widths={"A": 10, "B": 30, "C": 35, "D": 50, "E": 22,
                       "F": 24, "G": 16, "H": 16, "I": 16, "J": 20},
        filename="formations_jouri.xlsx",
    )


# ── POST handler (extracted to keep the main view readable) ───────────────────

def _handle_formation_post(request):
    delete_id    = request.POST.get("delete_id")
    formation_id = request.POST.get("formation_id")

    if delete_id:
        get_object_or_404(Formation, id=delete_id).delete()
        messages.success(request, "Formation supprimée avec succès.")
        return redirect("admin_dashboard:formations")

    title             = request.POST.get("title", "").strip()
    short_description = request.POST.get("short_description", "").strip()
    description       = request.POST.get("description", "").strip()
    category          = request.POST.get("category", "").strip()
    chef_name         = request.POST.get("chef_name", "").strip()
    duration          = request.POST.get("duration", "").strip()
    price             = request.POST.get("price") or None
    is_published      = request.POST.get("is_published") == "on"

    if not title:
        messages.error(request, "Le titre de la formation est obligatoire.")
        return redirect("admin_dashboard:formations")

    if formation_id:
        formation                    = get_object_or_404(Formation, id=formation_id)
        formation.title              = title
        formation.short_description  = short_description
        formation.description        = description
        formation.category           = category
        formation.chef_name          = chef_name
        formation.duration           = duration
        formation.price              = price
        formation.is_published       = is_published

        if request.FILES.get("image"):
            formation.image = request.FILES["image"]

        formation.save()
        messages.success(request, "Formation modifiée avec succès.")
    else:
        Formation.objects.create(
            title=title, short_description=short_description,
            description=description, category=category,
            chef_name=chef_name, duration=duration,
            price=price, is_published=is_published,
            image=request.FILES.get("image"),
        )
        messages.success(request, "Formation ajoutée avec succès.")

    return redirect("admin_dashboard:formations")