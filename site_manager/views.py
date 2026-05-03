from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib import messages

from admin_dashboard.models import (
    Formation,
    RegistrationRequest,
    Notification,
    ContactMessage,
    Student,
    StudentActivationCode,
)
from admin_dashboard.views.utils import create_and_send_student_activation_code

def resend_student_code(request):
    if request.method != "POST":
        return redirect("site_manager:login")

    email = request.POST.get("email", "").strip()

    if not email:
        return render(request, "site/login.html", {
            "message": "Veuillez saisir votre adresse e-mail.",
            "show_signup": True
        })

    student = Student.objects.filter(user__email=email).select_related("user").first()

    if not student or not student.user:
        return render(request, "site/login.html", {
            "message": "Aucun compte étudiant trouvé avec cet email.",
            "show_signup": True
        })

    create_and_send_student_activation_code(student.user, email)

    messages.success(
        request,
        "Un nouveau code d’activation a été envoyé à votre adresse e-mail."
    )
    return redirect("site_manager:login")


def login(request):
    message = ""
    show_signup = False

    if request.method == "POST":

        # 🔹 SI activation (on détecte avec "code")
        if "code" in request.POST:
            show_signup = True

            email = request.POST.get("email", "").strip()
            code = request.POST.get("code", "").strip()
            password = request.POST.get("password", "")
            confirm_password = request.POST.get("confirm_password", "")

            if password != confirm_password:
                message = "Les mots de passe ne correspondent pas."
                return render(request, "site/login.html", {
                    "message": message,
                    "show_signup": True
                })

            activation = (
                StudentActivationCode.objects
                .filter(email=email, code=code, is_used=False)
                .select_related("user")
                .first()
            )

            if not activation:
                message = "Code invalide."
                return render(request, "site/login.html", {
                    "message": message,
                    "show_signup": True
                })

            if activation.is_expired():
                message = "Code expiré."
                return render(request, "site/login.html", {
                    "message": message,
                    "show_signup": True
                })

            # 🔥 activer compte
            user = activation.user
            user.set_password(password)
            user.save()

            activation.is_used = True
            activation.save()

            student = Student.objects.filter(user=user).first()
            if student:
                student.is_new = False
                student.save()

            messages.success(request, "Compte activé avec succès.")
            return redirect("site_manager:login")

        else:
            # 🔹 LOGIN NORMAL (ton code original)
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                auth_login(request, user)

                if user.is_superuser or user.is_staff:
                    return redirect("admin_dashboard:admin_dashboard")

                if hasattr(user, "employee_profile"):
                    return redirect("/dashboard/teacher/")

                if hasattr(user, "student_profile"):
                    return redirect("/dashboard/student/")

                return redirect("site_manager:home")

            else:
                message = "Invalid username or password."

    return render(request, "site/login.html", {
        "message": message,
        "show_signup": show_signup
    })


def home(request):
    formations = Formation.objects.filter(is_published=True)
    return render(request, "site/home.html", {
        "formations": formations
    })


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        message = request.POST.get("message", "").strip()

        if not name or not email or not message:
            return render(request, "site/contact.html", {
                "error": "Veuillez remplir tous les champs obligatoires."
            })

        contact_message = ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            message=message,
        )

        Notification.objects.create(
            title="Nouveau message de contact",
            message=f"{contact_message.name} a envoyé un message via le formulaire de contact.",
            type="system",
            priority="low",
            is_read=False,
            related_object=contact_message.name,
        )

        return render(request, "site/contact.html", {
            "success": True
        })

    return render(request, "site/contact.html")


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        role = request.POST.get("role", "").strip()

        if not username or not email or not password or not confirm_password or not role:
            return render(request, "site/login.html", {
                "message": "Please fill in all required fields.",
                "show_signup": True,
            })

        if password != confirm_password:
            return render(request, "site/login.html", {
                "message": "Passwords do not match.",
                "show_signup": True,
            })

        if User.objects.filter(username=username).exists():
            return render(request, "site/login.html", {
                "message": "This username is already taken.",
                "show_signup": True,
            })

        if User.objects.filter(email=email).exists():
            return render(request, "site/login.html", {
                "message": "This email is already in use.",
                "show_signup": True,
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        auth_login(request, user)
        return redirect("site_manager:home")

    return redirect("site_manager:login")


def formation_detail(request, slug):
    formation = get_object_or_404(Formation, slug=slug, is_published=True)

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        registration = RegistrationRequest.objects.create(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            formation=formation,
            message=message,
            status="pending",
        )

        Notification.objects.create(
            title="Nouvelle demande d'inscription",
            message=f"{registration.first_name} {registration.last_name} a demandé une inscription à la formation {formation.title}.",
            type="student",
            priority="medium",
            is_read=False,
            related_object=f"{registration.first_name} {registration.last_name}"
        )

        return render(request, "site/formation_detail.html", {
            "formation": formation,
            "success": True,
        })

    return render(request, "site/formation_detail.html", {
        "formation": formation,
    })