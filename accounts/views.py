import logging
import email_service

logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

from .forms import PatientSignUpForm, DoctorSignUpForm
from .models import Doctor, Patient

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if hasattr(user, 'doctor'):
                return redirect('doctor_dashboard')
            elif hasattr(user, 'patient'):
                return redirect('patient_dashboard')
            else:
                return redirect('/admin/')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    # Log the user out and send them back to the login page
    logout(request)
    return redirect('login')


def patient_signup(request):
    if request.method == 'POST':
        form = PatientSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Patient.objects.create(
                user=user,
                contact_number=form.cleaned_data.get('contact_number')
            )
            try:
                email_service.send_email(
                    action="SIGNUP_WELCOME",
                    patient_email=user.email,
                    patient_name=user.first_name or user.username,
                )
                logger.info("Successfully sent Welcome Email!")
            except Exception as e:
                logger.warning(f"Failed to send welcome email: {e}")

            login(request, user)
            return redirect('patient_dashboard')
    else:
        form = PatientSignUpForm()
    return render(request, 'accounts/patient_signup.html', {'form': form})


def doctor_signup(request):
    if request.method == 'POST':
        form = DoctorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            Doctor.objects.create(
                user=user,
                department=form.cleaned_data.get('department'),
                degree=form.cleaned_data.get('degree')
            )
            try:
                email_service.send_email(
                    action="SIGNUP_WELCOME",
                    patient_email=user.email,
                    patient_name=f"Dr. {user.last_name or user.username}",
                )
                logger.info("Successfully sent Doctor Welcome Email!")
            except Exception as e:
                logger.warning(f"Failed to send welcome email: {e}")
            login(request, user)
            return redirect('doctor_dashboard')
    else:
        form = DoctorSignUpForm()
    return render(request, 'accounts/doctor_signup.html', {'form': form})
