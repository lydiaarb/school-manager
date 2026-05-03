
from django.urls import path
from . import views

app_name = "site_manager"

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.contact, name="contact"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
    path("formations/<slug:slug>/", views.formation_detail, name="formation_detail"),
    path("resend-student-code/", views.resend_student_code, name="resend_student_code"),
]