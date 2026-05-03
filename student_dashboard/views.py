from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now

from admin_dashboard.models import TimetableSession, AttendanceRecord, Notification, Invoice
from .decorators import student_required
import qrcode
from django.http import HttpResponse
from io import BytesIO

@login_required
@student_required
def student_qr_code(request):
    student = request.user.student_profile

    qr_data = f"student:{student.id}:{student.qr_token}"  

    qr = qrcode.make(qr_data)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    return HttpResponse(buffer.getvalue(), content_type="image/png")

@login_required
@student_required
def home(request):
    student = request.user.student_profile

    upcoming_sessions = TimetableSession.objects.filter(
        formation=student.formation,
        is_active=True
    ).select_related(
        "room",
        "teacher",
        "formation"
    ).order_by("day", "start_time")[:5]

    recent_attendance = AttendanceRecord.objects.filter(
        student=student
    ).select_related(
        "attendance_session__timetable_session"
    ).order_by("-scanned_at")[:5]

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by("-created_at")[:5]

    context = {
        "student": student,
        "upcoming_sessions": upcoming_sessions,
        "recent_attendance": recent_attendance,
        "notifications": notifications,
    }

    return render(request, "student_dashboard/home.html", context)


@login_required
@student_required
def timetable(request):
    student = request.user.student_profile

    sessions = TimetableSession.objects.filter(
        formation=student.formation,
        is_active=True
    ).select_related(
        "room",
        "teacher",
        "formation"
    ).order_by("day", "start_time")

    context = {
        "student": student,
        "sessions": sessions,
    }

    return render(request, "student_dashboard/timetable.html", context)


@login_required
@student_required
def attendance(request):
    student = request.user.student_profile

    records = AttendanceRecord.objects.filter(
        student=student
    ).select_related(
        "attendance_session__timetable_session"
    ).order_by("-scanned_at")

    context = {
        "student": student,
        "records": records,
    }

    return render(request, "student_dashboard/attendance.html", context)


@login_required
@student_required
def payments(request):
    student = request.user.student_profile

    invoices = (
        Invoice.objects
        .filter(student=student)
        .select_related("formation")
        .prefetch_related("payments")
        .order_by("-created_at")
    )

    total_due = sum(invoice.total_amount for invoice in invoices)
    total_paid = sum(invoice.paid_amount for invoice in invoices)
    remaining = total_due - total_paid

    context = {
        "student": student,
        "invoices": invoices,
        "total_due": total_due,
        "total_paid": total_paid,
        "remaining": remaining,
    }

    return render(request, "student_dashboard/payments.html", context)

@login_required
@student_required
def notifications(request):
    student = request.user.student_profile

    notifications_qs = Notification.objects.filter(
        recipient=request.user
    ).order_by("-created_at")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        notifications_qs = notifications_qs.filter(
            Q(title__icontains=q) | Q(message__icontains=q)
        )

    if status == "unread":
        notifications_qs = notifications_qs.filter(is_read=False)
    elif status == "read":
        notifications_qs = notifications_qs.filter(is_read=True)

    total_notifications = notifications_qs.count()
    unread_notifications = notifications_qs.filter(is_read=False).count()
    today_notifications = notifications_qs.filter(created_at__date=now().date()).count()

    paginator = Paginator(notifications_qs, 8)
    page_number = request.GET.get("page")
    notifications_page = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()

    context = {
        "student": student,
        "notifications": notifications_page,
        "total_notifications": total_notifications,
        "unread_notifications": unread_notifications,
        "today_notifications": today_notifications,
        "query_string": query_string,
    }

    return render(request, "student_dashboard/notifications.html", context)


@login_required
@student_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    messages.success(request, "Notification marquée comme lue.")
    return redirect("student_dashboard:notifications")


@login_required
@student_required
def mark_all_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect("student_dashboard:notifications")


@login_required
@student_required
def student_logout(request):
    logout(request)
    return redirect("/site/login/")