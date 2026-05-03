from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/site/login/")

        student = getattr(request.user, "student_profile", None)
        if not student:
            messages.error(request, "Accès étudiant refusé.")
            return redirect("/site/login/")

        return view_func(request, *args, **kwargs)

    return _wrapped_view