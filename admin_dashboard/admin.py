from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "type", "category", "ref", "method", "status", "amount")
    list_filter = ("type", "status", "category")
    search_fields = ("ref", "category", "method")
