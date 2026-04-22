import datetime

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Doctor(models.Model):
    # Links this profile to a standard Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # You can add more fields here later (e.g., specialty, phone number)
    department = models.CharField(max_length=100, blank=True, null=True)
    degree = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        name = f"Dr. {self.user.first_name} {self.user.last_name}"
        if self.degree:
            return f"{name} ({self.degree})"
        return name

    def get_upcoming_appointments(self):
        # We import Appointment here to avoid "circular import" errors
        from core.models import Appointment
        today = datetime.date.today()

        # Fetches appointments from today onward
        return self.appointments.filter(
            time_slot__date__gte=today
        ).order_by('time_slot__date', 'time_slot__start_time')


class Patient(models.Model):
    # Links this profile to a standard Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # You can add more fields here later (e.g., date of birth, blood group)
    contact_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
