from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static


def test_tailwind(request):
    return render(request, "test.html")


urlpatterns = [
    path("", RedirectView.as_view(url="/site/", permanent=False)),
    path("__reload__/", include("django_browser_reload.urls")),

    path("admin/", admin.site.urls),

    path("site/", include("site_manager.urls")),
    path("accounts/", include("accounts.urls")),

    path("dashboard/admin/", include("admin_dashboard.urls")),
    path("dashboard/student/", include("student_dashboard.urls")),
    path("dashboard/teacher/", include("teacher_dashboard.urls")),
    path("test/", test_tailwind),
]

# serve uploaded images in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)





