from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Customer', 'Customer'),
        ('Pharmacist', 'Pharmacist'),
        ('Admin', 'Admin'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='Customer')
    is_admin = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Health Profile fields
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True, help_text="Comma-separated allergies")
    medical_history = models.TextField(blank=True, null=True, help_text="Chronic conditions or previous medical logs")
    
    # MFA setting
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Align is_admin and is_staff with the selected role
        if self.role == 'Admin':
            self.is_admin = True
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'Pharmacist':
            self.is_admin = False
            self.is_staff = True
            self.is_superuser = False
        else:
            self.is_admin = False
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

class FamilyProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_members')
    name = models.CharField(max_length=100)
    relation = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    allergies = models.TextField(blank=True, null=True)
    medical_history = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.relation}) - User: {self.user.username}"

class MedicationReminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text="e.g. 1 tablet, 5ml syrup")
    time = models.TimeField()
    frequency = models.CharField(max_length=100, default="Daily", help_text="e.g., Daily, Weekly, Mon-Wed-Fri")
    is_active = models.BooleanField(default=True)
    adherence_logs = models.TextField(default="[]", help_text="JSON list of logged takes, e.g., ['2026-06-23 taken', '2026-06-24 missed']")

    def __str__(self):
        return f"Reminder: {self.medicine_name} at {self.time} for {self.user.username}"
