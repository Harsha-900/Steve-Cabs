from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [('customer','Customer'),('driver','Driver')]
    LANGUAGE_CHOICES = [('en','English'),('ta','Tamil'),('kn','Kannada'),('hi','Hindi')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    is_available = models.BooleanField(default=False)
    current_location = models.JSONField(null=True, blank=True)

    # # Optional profile image (navbar / dashboards use this when set)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)