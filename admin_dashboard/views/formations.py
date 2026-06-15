"""
views/formations.py — Formation CRUD + Excel export.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import Formation, FormationImage, FormationObjectif
from .utils import build_excel_response, admin_required

from django.contrib import admin
from django.utils.html import format_html


class FormationImageInline(admin.TabularInline):
    model = FormationImage
    extra = 3
    fields = ('image', 'caption', 'order', 'preview')
    readonly_fields = ('preview',)
 
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:8px;object-fit:cover;">',
                obj.image.url
            )
        return "—"
    preview.short_description = "Aperçu"
 
 
class FormationObjectifInline(admin.TabularInline):
    model = FormationObjectif
    extra = 4
    fields = ('texte', 'order')
    verbose_name = "Objectif"
    verbose_name_plural = "Objectifs pédagogiques"
 
 
# ── Formation Admin ─────────────────────────────────────────
 
@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display   = ('title', 'category', 'chef_name', 'price', 'is_published', 'thumbnail')
    list_filter    = ('is_published', 'category')
    search_fields  = ('title', 'chef_name', 'category')
    prepopulated_fields = {'slug': ('title',)}
    inlines        = [FormationImageInline, FormationObjectifInline]
 
    fieldsets = (
        ("Informations générales", {
            'fields': ('title', 'slug', 'category', 'short_description', 'description', 'image')
        }),
        ("Encadrement & Durée", {
            'fields': ('chef_name', 'duration', 'price')
        }),
        ("Publication", {
            'fields': ('is_published',)
        }),
    )
 
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px;object-fit:cover;">',
                obj.image.url
            )
        return "—"
    thumbnail.short_description = "Photo"
 


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
        formation = Formation.objects.create(
            title=title, short_description=short_description,
            description=description, category=category,
            chef_name=chef_name, duration=duration,
            price=price, is_published=is_published,
            image=request.FILES.get("image"),
        )
        messages.success(request, "Formation ajoutée avec succès.")

    # Save objectives from the form
    objectif_textes = request.POST.getlist("objectif_texte[]")
    objectif_orders = request.POST.getlist("objectif_order[]")
    objectif_ids    = request.POST.getlist("objectif_id[]")

    objectif_rows = []
    for idx, texte in enumerate(objectif_textes):
        texte = texte.strip()
        if not texte:
            continue

        try:
            order = int(objectif_orders[idx]) if idx < len(objectif_orders) else idx
        except (ValueError, TypeError):
            order = idx

        objectif_rows.append({
            "id": objectif_ids[idx] if idx < len(objectif_ids) else None,
            "texte": texte,
            "order": order,
        })

    if formation_id:
        sent_ids = [int(i) for i in objectif_ids if i.isdigit()]
        if sent_ids:
            FormationObjectif.objects.filter(formation=formation).exclude(id__in=sent_ids).delete()
        else:
            FormationObjectif.objects.filter(formation=formation).delete()

        for row in objectif_rows:
            if row["id"] and str(row["id"]).isdigit():
                objectif = FormationObjectif.objects.filter(
                    id=int(row["id"]), formation=formation
                ).first()
                if objectif:
                    objectif.texte = row["texte"]
                    objectif.order = row["order"]
                    objectif.save()
                    continue

            FormationObjectif.objects.create(
                formation=formation,
                texte=row["texte"],
                order=row["order"],
            )
    else:
        for row in objectif_rows:
            FormationObjectif.objects.create(
                formation=formation,
                texte=row["texte"],
                order=row["order"],
            )

    return redirect("admin_dashboard:formations")