from .models import Notification


def admin_notification_count(request):
    unread_count = Notification.objects.filter(is_read=False).count()
    return {
        "admin_unread_notifications_count": unread_count
    }
def admin_notifications(request):
    if request.user.is_authenticated:
        return {
            "admin_unread_notifications_count": Notification.objects.filter(is_read=False).count()
        }
    return {"admin_unread_notifications_count": 0}