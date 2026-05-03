from django.shortcuts import redirect
from django.urls import reverse


class ForceTeacherPasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            employee = getattr(request.user, "employee_profile", None)

            if employee and employee.role == "enseignant" and employee.must_change_password:
                allowed_urls = [
                    reverse("teacher_dashboard:change_password"),
                    reverse("teacher_dashboard:logout"),
                    "/site/login/",
                ]

                if request.path not in allowed_urls:
                    return redirect("teacher_dashboard:change_password")

        return self.get_response(request)