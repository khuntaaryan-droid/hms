import datetime
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Doctor, Patient
from .models import TimeSlot, Appointment


def make_doctor(username='dr_test', first_name='Test', last_name='Doctor',
                department='General', degree='MBBS'):
    user = User.objects.create_user(username=username, password='pass1234',
                                    first_name=first_name, last_name=last_name,
                                    email=f'{username}@hospital.com')
    doctor = Doctor.objects.create(user=user, department=department, degree=degree)
    return user, doctor


def make_patient(username='pat_test', first_name='Pat', last_name='Patient'):
    user = User.objects.create_user(username=username, password='pass1234',
                                    first_name=first_name, last_name=last_name,
                                    email=f'{username}@email.com')
    patient = Patient.objects.create(user=user, contact_number='9999999999')
    return user, patient


def make_slot(doctor, date=None, start='09:00', end='10:00', is_booked=False):
    if date is None:
        date = timezone.now().date() + datetime.timedelta(days=1)
    start_time = datetime.datetime.strptime(start, '%H:%M').time()
    end_time = datetime.datetime.strptime(end, '%H:%M').time()
    return TimeSlot.objects.create(
        doctor=doctor,
        date=date,
        start_time=start_time,
        end_time=end_time,
        is_booked=is_booked,
    )


class TimeSlotModelTest(TestCase):
    def setUp(self):
        _, self.doctor = make_doctor()

    def test_timeslot_str(self):
        slot = make_slot(self.doctor)
        self.assertIn('09:00', str(slot))
        self.assertIn('10:00', str(slot))

    def test_timeslot_default_not_booked(self):
        slot = make_slot(self.doctor)
        self.assertFalse(slot.is_booked)

    def test_clean_raises_if_end_before_start(self):
        slot = TimeSlot(
            doctor=self.doctor,
            date=timezone.now().date(),
            start_time='10:00',
            end_time='09:00',
        )
        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_clean_raises_if_end_equals_start(self):
        slot = TimeSlot(
            doctor=self.doctor,
            date=timezone.now().date(),
            start_time='10:00',
            end_time='10:00',
        )
        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_clean_raises_if_start_not_15_min_interval(self):
        slot = TimeSlot(
            doctor=self.doctor,
            date=timezone.now().date(),
            start_time='10:07',
            end_time='11:00',
        )
        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_clean_raises_if_end_not_15_min_interval(self):
        slot = TimeSlot(
            doctor=self.doctor,
            date=timezone.now().date(),
            start_time='10:00',
            end_time='10:50',
        )
        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_clean_passes_for_valid_slot(self):
        slot = TimeSlot(
            doctor=self.doctor,
            date=timezone.now().date(),
            start_time='10:00',
            end_time='10:30',
        )
        slot.full_clean()   # should not raise


class AppointmentModelTest(TestCase):
    def setUp(self):
        _, self.doctor = make_doctor()
        _, self.patient = make_patient()
        self.slot = make_slot(self.doctor)

    def test_appointment_str(self):
        appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, time_slot=self.slot
        )
        self.assertIn('Pat Patient', str(appt))
        self.assertIn('Test Doctor', str(appt))

    def test_appointment_created_at_set_automatically(self):
        appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, time_slot=self.slot
        )
        self.assertIsNotNone(appt.created_at)

    def test_one_slot_cannot_have_two_appointments(self):
        Appointment.objects.create(patient=self.patient, doctor=self.doctor, time_slot=self.slot)
        _, patient2 = make_patient(username='pat2')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Appointment.objects.create(patient=patient2, doctor=self.doctor, time_slot=self.slot)


class DoctorDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.doc_user, self.doctor = make_doctor()
        self.client.login(username='dr_test', password='pass1234')
        self.url = reverse('doctor_dashboard')

    def test_dashboard_loads_for_doctor(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_rejects_non_doctor(self):
        pat_user, _ = make_patient()
        self.client.login(username='pat_test', password='pass1234')
        response = self.client.get(self.url)
        # Non-doctors should see the error page (200 with error template)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only doctors')

    def test_post_creates_timeslots(self):
        future_date = (timezone.now().date() + datetime.timedelta(days=1)).isoformat()
        response = self.client.post(self.url, {
            'date': future_date,
            'start_time': '09:00',
            'end_time': '11:00',
        })
        self.assertRedirects(response, self.url)
        self.assertEqual(TimeSlot.objects.filter(doctor=self.doctor).count(), 2)

    def test_post_invalid_time_shows_error(self):
        future_date = (timezone.now().date() + datetime.timedelta(days=1)).isoformat()
        response = self.client.post(self.url, {
            'date': future_date,
            'start_time': 'bad',
            'end_time': '11:00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get('error_message'))

    def test_post_start_after_end_creates_no_slots(self):
        """When start >= end the while-loop creates nothing and the view redirects."""
        future_date = (timezone.now().date() + datetime.timedelta(days=1)).isoformat()
        before_count = TimeSlot.objects.filter(doctor=self.doctor).count()
        response = self.client.post(self.url, {
            'date': future_date,
            'start_time': '12:00',
            'end_time': '10:00',
        })
        # View redirects back and no new slots are created
        self.assertRedirects(response, self.url)
        self.assertEqual(TimeSlot.objects.filter(doctor=self.doctor).count(), before_count)


class PatientDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pat_user, self.patient = make_patient()
        _, self.doctor = make_doctor()
        self.client.login(username='pat_test', password='pass1234')
        self.url = reverse('patient_dashboard')

    def test_dashboard_loads_for_patient(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_rejects_non_patient(self):
        self.client.login(username='dr_test', password='pass1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only patients')

    def test_shows_available_slots(self):
        make_slot(self.doctor)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['slots']), 1)

    def test_booked_slot_not_shown(self):
        make_slot(self.doctor, is_booked=True)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['slots']), 0)

    def test_filter_by_doctor(self):
        _, doctor2 = make_doctor(username='dr2', last_name='Second')
        make_slot(self.doctor)
        make_slot(doctor2)
        response = self.client.get(self.url, {'doctor': self.doctor.pk})
        for slot in response.context['slots']:
            self.assertEqual(slot.doctor, self.doctor)


class BookAppointmentViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pat_user, self.patient = make_patient()
        _, self.doctor = make_doctor()
        self.slot = make_slot(self.doctor)
        self.client.login(username='pat_test', password='pass1234')

    def test_get_redirects_to_patient_dashboard(self):
        url = reverse('book_appointment', args=[self.slot.pk])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('patient_dashboard'))

    def test_post_without_google_creds_redirects_to_authorize(self):
        url = reverse('book_appointment', args=[self.slot.pk])
        response = self.client.post(url)
        # Don't follow the chain — just confirm the first redirect target
        self.assertRedirects(response, reverse('google_authorize'), fetch_redirect_response=False)

    def test_post_with_google_creds_redirects_to_process(self):
        session = self.client.session
        session['google_creds'] = {'token': 'fake'}
        session.save()
        url = reverse('book_appointment', args=[self.slot.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('process_google_booking'), fetch_redirect_response=False)

    def test_unauthenticated_redirected(self):
        self.client.logout()
        url = reverse('book_appointment', args=[self.slot.pk])
        response = self.client.post(url)
        self.assertNotEqual(response.status_code, 200)


class ProcessGoogleBookingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pat_user, self.patient = make_patient()
        _, self.doctor = make_doctor()
        self.slot = make_slot(self.doctor)
        self.client.login(username='pat_test', password='pass1234')

    def _set_session(self, slot_id=None, creds=None):
        session = self.client.session
        if slot_id:
            session['booking_slot_id'] = slot_id
        if creds:
            session['google_creds'] = creds
        session.save()

    def test_missing_session_data_redirects_to_patient_dashboard(self):
        response = self.client.get(reverse('process_google_booking'))
        self.assertRedirects(response, reverse('patient_dashboard'))

    @patch('core.views.build')
    @patch('email_service.resend.Emails.send')
    def test_booking_creates_appointment_and_marks_slot_booked(self, mock_send, mock_build):
        mock_send.return_value = {'id': 'fake-id'}
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        self._set_session(
            slot_id=self.slot.pk,
            creds={
                'token': 'tok', 'refresh_token': 'ref',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': 'cid', 'client_secret': 'csec',
                'scopes': ['https://www.googleapis.com/auth/calendar.events'],
            }
        )
        self.client.get(reverse('process_google_booking'))

        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_booked)
        self.assertTrue(Appointment.objects.filter(time_slot=self.slot).exists())

    @patch('core.views.build')
    @patch('email_service.resend.Emails.send')
    def test_booking_sends_confirmation_email(self, mock_send, mock_build):
        mock_send.return_value = {'id': 'fake-id'}
        mock_build.return_value = MagicMock()

        self._set_session(
            slot_id=self.slot.pk,
            creds={
                'token': 'tok', 'refresh_token': 'ref',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': 'cid', 'client_secret': 'csec',
                'scopes': ['https://www.googleapis.com/auth/calendar.events'],
            }
        )
        self.client.get(reverse('process_google_booking'))

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        self.assertIn('pat_test@email.com', call_args['to'])
        self.assertIn('Confirmation', call_args['subject'])

    @patch('core.views.build')
    @patch('email_service.resend.Emails.send', side_effect=Exception('Resend down'))
    def test_booking_succeeds_even_if_email_fails(self, mock_send, mock_build):
        mock_build.return_value = MagicMock()
        self._set_session(
            slot_id=self.slot.pk,
            creds={
                'token': 'tok', 'refresh_token': 'ref',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': 'cid', 'client_secret': 'csec',
                'scopes': ['https://www.googleapis.com/auth/calendar.events'],
            }
        )
        response = self.client.get(reverse('process_google_booking'))
        self.assertRedirects(response, reverse('patient_dashboard'))
        self.assertTrue(Appointment.objects.filter(time_slot=self.slot).exists())

    @patch('core.views.build')
    @patch('email_service.resend.Emails.send')
    def test_already_booked_slot_not_double_booked(self, mock_send, mock_build):
        mock_send.return_value = {'id': 'fake-id'}
        mock_build.return_value = MagicMock()

        self.slot.is_booked = True
        self.slot.save()

        self._set_session(
            slot_id=self.slot.pk,
            creds={
                'token': 'tok', 'refresh_token': 'ref',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': 'cid', 'client_secret': 'csec',
                'scopes': ['https://www.googleapis.com/auth/calendar.events'],
            }
        )
        self.client.get(reverse('process_google_booking'))
        self.assertEqual(Appointment.objects.filter(time_slot=self.slot).count(), 0)
