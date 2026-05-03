from django.contrib import admin
from .models import Formation


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "chef_name", "price", "is_published", "created_at")
    list_filter = ("is_published", "category")
    search_fields = ("title", "short_description", "chef_name")
    prepopulated_fields = {"slug": ("title",)}