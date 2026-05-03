from django.db import models
from django.utils.text import slugify
import uuid
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Formation(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="formations/", blank=True, null=True)

    category = models.CharField(max_length=100, blank=True)
    chef_name = models.CharField(max_length=150, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Transaction(models.Model):
    TYPE_CHOICES = [
        ("Income", "Income"),
        ("Expense", "Expense"),
    ]

    STATUS_CHOICES = [
        ("Paid", "Paid"),
        ("Pending", "Pending"),
        ("Cancelled", "Cancelled"),
    ]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=100)
    ref = models.CharField(max_length=100, unique=True)
    method = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Paid")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.ref}"



class Student(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("paid", "Paid"),
        ("partial", "Partial"),
        ("pending", "Pending"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile"
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name="students"
    )

    start_date = models.DateField()

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending"
    )

    attendance_percentage = models.PositiveIntegerField(default=0)

    student_code = models.CharField(max_length=20, unique=True, blank=True)
    qr_token = models.CharField(max_length=100, unique=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_new = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.student_code:
            last_student = Student.objects.order_by("-id").first()
            if last_student and last_student.student_code:
                last_number = int(last_student.student_code.replace("STD", ""))
                new_number = last_number + 1
            else:
                new_number = 1

            self.student_code = f"STD{new_number:04d}"

        if not self.qr_token:
            self.qr_token = str(uuid.uuid4())

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class StudentActivationCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_activation_codes"
    )
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def get_expiry():
        return timezone.now() + timedelta(minutes=15)

    def __str__(self):
        return f"{self.email} - {self.code}"

class Employee(models.Model):
    ROLE_CHOICES = [
        ("enseignant", "Enseignant"),
        ("administratif", "Administratif"),
        ("comptable", "Comptable"),
        ("staff", "Staff"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile"
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="enseignant"
    )

    specialty = models.CharField(max_length=100, blank=True)
    experience_years = models.PositiveIntegerField(default=0)

    formation = models.ForeignKey(
        Formation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees"
    )

    must_change_password = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Room(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class TimetableSession(models.Model):
    DAY_CHOICES = [
        ("saturday", "Saturday"),
        ("sunday","Sunday"),
        ("monday", "Monday"),
        ("tuesday", "Tuesday"),
        ("wednesday", "Wednesday"),
        ("thursday", "Thursday"),
        ("friday", "Friday"),
        
    ]

    COLOR_CHOICES = [
        ("blue", "Blue"),
        ("emerald", "Emerald"),
        ("violet", "Violet"),
        ("amber", "Amber"),
        ("rose", "Rose"),
        ("cyan", "Cyan"),
        ("slate", "Slate"),
    ]

    title = models.CharField(max_length=200)
    formation = models.ForeignKey(
        "Formation",
        on_delete=models.CASCADE,
        related_name="timetable_sessions"
    )
    teacher = models.ForeignKey(
    Employee,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="timetable_sessions"
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timetable_sessions"
    )

    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default="blue")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day", "start_time", "end_time"]

    def __str__(self):
        return f"{self.title} - {self.get_day_display()}"

    @property
    def time_label(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("payment", "Payment"),
        ("timetable", "Timetable"),
        ("system", "System"),
        ("warning", "Warning"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="low")
    is_read = models.BooleanField(default=False)

    related_object = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional label like student name, formation title, invoice ref, etc."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
class RegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name="registration_requests"
    )

    message = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.formation.title}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.email}"

class AttendanceSession(models.Model):
    timetable_session = models.ForeignKey(
        TimetableSession,
        on_delete=models.CASCADE,
        related_name="attendance_sessions"
    )
    date = models.DateField()
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("timetable_session", "date")

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("late", "Late"),
        ("absent", "Absent"),
    ]

    attendance_session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records"
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="present")
    scanned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("attendance_session", "student")

class SchoolSettings(models.Model):
    school_name = models.CharField(max_length=200, default="Centre de formation Jouri")
    slogan      = models.CharField(max_length=255, blank=True)
    phone       = models.CharField(max_length=50, blank=True)
    email       = models.EmailField(blank=True)
    website     = models.URLField(blank=True)
    address     = models.TextField(blank=True)
    description = models.TextField(blank=True)
    facebook    = models.URLField(blank=True)
    instagram   = models.URLField(blank=True)
    logo        = models.ImageField(upload_to="school/", blank=True, null=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.school_name
    
class Invoice(models.Model):
    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partial"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    ]

    student = models.ForeignKey("Student", on_delete=models.CASCADE, related_name="invoices")
    formation = models.ForeignKey("Formation", on_delete=models.CASCADE)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unpaid")

    created_at = models.DateTimeField(auto_now_add=True)

    def update_status(self):
        if self.paid_amount >= self.total_amount:
            self.status = "paid"
        elif self.paid_amount > 0:
            self.status = "partial"
        else:
            self.status = "unpaid"

        from django.utils import timezone
        if self.due_date < timezone.now().date() and self.status != "paid":
            self.status = "overdue"

        self.save()

class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, blank=True)

    date = models.DateField(auto_now_add=True)
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

class EmployeePayment(models.Model):
    employee = models.ForeignKey("Employee", on_delete=models.CASCADE, related_name="payments")

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_month = models.CharField(max_length=20)

    status = models.CharField(max_length=20, default="pending")
    method = models.CharField(max_length=50, blank=True)

    date = models.DateField(auto_now_add=True)