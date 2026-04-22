import json
import logging
import email_service

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta, date

from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import TimeSlot, Appointment
from accounts.models import Doctor, Patient

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CREDENTIALS_FILE = 'credentials.json'


@login_required
def doctor_dashboard(request):
    try:
        doctor_profile = request.user.doctor
    except Doctor.DoesNotExist:
        return render(request, 'core/error.html', {'message': 'Only doctors can view this page.'})

    today = timezone.now().date()
    error_message = None

    if request.method == 'POST':
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')

        try:
            dummy_date = date.today()
            start_dt = datetime.strptime(start_time_str, '%H:%M').time()
            end_dt = datetime.strptime(end_time_str, '%H:%M').time()

            current_time = datetime.combine(dummy_date, start_dt)
            final_end_time = datetime.combine(dummy_date, end_dt)

            slots_to_create = []
            while current_time < final_end_time:
                next_time = current_time + timedelta(hours=1)

                if next_time > final_end_time:
                    break

                new_slot = TimeSlot(
                    doctor=doctor_profile,
                    date=date_str,
                    start_time=current_time.time(),
                    end_time=next_time.time()
                )
                new_slot.full_clean()
                slots_to_create.append(new_slot)
                current_time = next_time
            if slots_to_create:
                TimeSlot.objects.bulk_create(slots_to_create)
            return redirect('doctor_dashboard')
        except ValidationError as e:
            if hasattr(e, 'messages'):
                error_message = e.messages[0]
            else:
                error_message = str(e)
        except Exception as e:
            error_message = "Invalid time format selected."

    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor_profile,
        time_slot__date__gte=today,
    ).select_related('patient__user', 'time_slot').order_by('time_slot__date', 'time_slot__start_time')

    available_slots = TimeSlot.objects.filter(
        doctor=doctor_profile,
        is_booked=False,
        date__gte=today,
    ).order_by('date', 'start_time')

    all_my_slots = TimeSlot.objects.filter(doctor=doctor_profile)
    booked_times = {}
    for slot in all_my_slots:
        date_str = slot.date.strftime('%Y-%m-%d')
        if date_str not in booked_times:
            booked_times[date_str] = []

        c_time = datetime.combine(slot.date, slot.start_time)
        e_time = datetime.combine(slot.date, slot.end_time)

        while c_time < e_time:
            booked_times[date_str].append(c_time.strftime('%H:%M'))
            c_time += timedelta(minutes=15)

    context = {
        'appointments': upcoming_appointments,
        'slots': available_slots,
        'error_message': error_message,
        'booked_times_json': json.dumps(booked_times)
    }
    return render(request, 'core/doctor_dashboard.html', context)


@login_required
def patient_dashboard(request):
    now = timezone.now()
    today = now.date()
    current_time = now.time()
    try:
        patient_profile = request.user.patient
    except Patient.DoesNotExist:
        return render(request, 'core/error.html', {'message': 'Only patients can view this page.'})

    all_doctors = Doctor.objects.all()
    available_slots = TimeSlot.objects.filter(
        Q(is_booked=False) &(Q(date__gt=today) | Q(date=today, start_time__gte=current_time))
    ).order_by('date', 'start_time')

    selected_doctor_id = request.GET.get('doctor')

    if selected_doctor_id:
        available_slots = available_slots.filter(doctor_id=selected_doctor_id)

    my_appointments = Appointment.objects.filter(patient=patient_profile).order_by('time_slot__date')

    context = {
        'slots': available_slots,
        'appointments': my_appointments,
        'doctors': all_doctors,
        'selected_doctor_id': selected_doctor_id,
    }
    return render(request, 'core/patient_dashboard.html', context)


@login_required
def book_appointment(request, slot_id):
    if request.method == 'POST':
        request.session['booking_slot_id'] = slot_id
        if 'google_creds' not in request.session:
            return redirect('google_authorize')
        return redirect('process_google_booking')
    return redirect('patient_dashboard')


@login_required
def google_authorize(request):
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri='http://127.0.0.1:8000/oauth2callback/'
    )
    authorization_url, state = flow.authorization_url(
        prompt='consent',
        access_type='offline'
    )
    request.session['state'] = state
    request.session['code_verifier'] = flow.code_verifier
    return redirect(authorization_url)


def oauth2callback(request):
    state = request.session.get('state')

    if not state:
        return redirect('patient_dashboard')  # Safety catch

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri='http://127.0.0.1:8000/oauth2callback/'
    )
    code_verifier = request.session.get('code_verifier')
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials
    request.session['google_creds'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    return redirect('process_google_booking')


@login_required
def process_google_booking(request):
    slot_id = request.session.get('booking_slot_id')
    creds_data = request.session.get('google_creds')

    if not slot_id or not creds_data:
        return redirect('patient_dashboard')

    slot = get_object_or_404(TimeSlot, id=slot_id)
    try:
        patient_profile = request.user.patient
    except Exception:
        return redirect('patient_dashboard')

    if not slot.is_booked:
        Appointment.objects.create(patient=patient_profile, doctor=slot.doctor, time_slot=slot)
        slot.is_booked = True
        slot.save()

        creds = Credentials(**creds_data)
        service = build('calendar', 'v3', credentials=creds)

        start_time_str = datetime.combine(slot.date, slot.start_time).isoformat() + 'Z'
        end_time_str = datetime.combine(slot.date, slot.end_time).isoformat() + 'Z'

        event_data = {
            'summary': f'Medical Appointment: {patient_profile.user.first_name} {patient_profile.user.last_name}'
                       f' & Dr. {slot.doctor.user.last_name}',
            'description': 'Automated booking from Mini-HMS.',
            'start': {
                'dateTime': start_time_str,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time_str,
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': slot.doctor.user.email},
            ],
            'reminders': {'useDefault': True},
        }
        try:
            service.events().insert(calendarId='primary', body=event_data, sendUpdates='all').execute()
        except Exception as e:
            logger.warning(f"Calendar API Error: {e}")

    if 'booking_slot_id' in request.session:
        del request.session['booking_slot_id']
    try:
        email_service.send_email(
            action="BOOKING_CONFIRMATION",
            patient_email=patient_profile.user.email,
            patient_name=patient_profile.user.first_name,
            doctor_name=slot.doctor.user.last_name,
            date=slot.date.strftime('%Y-%m-%d'),
            time=slot.start_time.strftime('%H:%M'),
        )
        logger.info("Successfully sent Booking Confirmation Email!")
    except Exception as e:
        logger.warning(f"Failed to trigger email service: {e}")

    # Clean up the session data so the next booking starts fresh
    if 'booking_slot_id' in request.session:
        del request.session['booking_slot_id']
    return redirect('patient_dashboard')
