from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('formateur', 'Formateur'),
        ('stagiaire', 'Stagiaire'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='stagiaire')

    def __str__(self):
        return f"{self.username} ({self.role})"
