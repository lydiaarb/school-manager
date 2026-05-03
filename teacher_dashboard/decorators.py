from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/site/login/")

        employee = getattr(request.user, "employee_profile", None)

        if not employee or employee.role != "enseignant":
            messages.error(request, "Accès enseignant refusé.")
            return redirect("/site/login/")

        return view_func(request, *args, **kwargs)

    return _wrapped_view