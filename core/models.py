from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import Doctor, Patient

# Create your models here.
class TimeSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)

    def clean(self):
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError("End time must be after the start time.")

            allowed_minutes = [0, 15, 30, 45]
            if self.start_time.minute not in allowed_minutes:
                raise ValidationError("Start time must be in 15-minute intervals (e.g., 10:00, 10:15).")
            if self.end_time.minute not in allowed_minutes:
                raise ValidationError("End time must be in 15-minute intervals.")

    def __str__(self):
        return f"{self.doctor} - {self.date} ({self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')})"

class Appointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')

    time_slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} booking with {self.doctor} on {self.time_slot.date}"
