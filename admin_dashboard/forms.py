from django import forms
from .models import Formation, Transaction



class FormationForm(forms.ModelForm):
    class Meta:
        model = Formation
        fields = [
            "title",
            "short_description",
            "description",
            "image",
            "category",
            "chef_name",
            "duration",
            "price",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "short_description": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300",
                "rows": 5
            }),
            "category": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "chef_name": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "duration": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "price": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "is_published": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-400"
            }),
        }
      

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "type", "category", "ref", "method", "status", "amount", "note"]
        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "type": forms.Select(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "category": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "ref": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "method": forms.TextInput(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "status": forms.Select(attrs={
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "amount": forms.NumberInput(attrs={
                "step": "0.01",
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
            "note": forms.Textarea(attrs={
                "rows": 4,
                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300"
            }),
        }