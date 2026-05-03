from admin_dashboard.models import SchoolSettings


def school_settings(request):
    settings_obj, _ = SchoolSettings.objects.get_or_create(id=1)
    return {
        "public_school_settings": settings_obj
    }