from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .models import Doctor, Patient


class PatientModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='john_doe',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            email='john@example.com',
        )
        self.patient = Patient.objects.create(user=self.user, contact_number='9876543210')

    def test_patient_str(self):
        self.assertEqual(str(self.patient), 'John Doe')

    def test_patient_linked_to_user(self):
        self.assertEqual(self.patient.user, self.user)

    def test_patient_contact_number(self):
        self.assertEqual(self.patient.contact_number, '9876543210')

    def test_patient_contact_number_optional(self):
        user2 = User.objects.create_user(username='jane', password='pass')
        patient2 = Patient.objects.create(user=user2)
        self.assertIsNone(patient2.contact_number)


class DoctorModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dr_smith',
            password='testpass123',
            first_name='Adam',
            last_name='Smith',
            email='dr.smith@example.com',
        )
        self.doctor = Doctor.objects.create(
            user=self.user,
            department='Cardiology',
            degree='MBBS',
        )

    def test_doctor_str_with_degree(self):
        self.assertEqual(str(self.doctor), 'Dr. Adam Smith (MBBS)')

    def test_doctor_str_without_degree(self):
        user2 = User.objects.create_user(username='dr2', password='pass',
                                         first_name='Jane', last_name='Roe')
        doctor2 = Doctor.objects.create(user=user2)
        self.assertEqual(str(doctor2), 'Dr. Jane Roe')

    def test_doctor_department(self):
        self.assertEqual(self.doctor.department, 'Cardiology')

    def test_doctor_optional_fields(self):
        user3 = User.objects.create_user(username='dr3', password='pass')
        doctor3 = Doctor.objects.create(user=user3)
        self.assertIsNone(doctor3.department)
        self.assertIsNone(doctor3.degree)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('login')
        self.user = User.objects.create_user(username='testuser', password='pass1234')
        Patient.objects.create(user=self.user)

    def test_login_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_login_patient_redirects_to_patient_dashboard(self):
        response = self.client.post(self.url, {'username': 'testuser', 'password': 'pass1234'})
        self.assertRedirects(response, reverse('patient_dashboard'))

    def test_login_doctor_redirects_to_doctor_dashboard(self):
        doc_user = User.objects.create_user(username='docuser', password='pass1234')
        Doctor.objects.create(user=doc_user)
        response = self.client.post(self.url, {'username': 'docuser', 'password': 'pass1234'})
        self.assertRedirects(response, reverse('doctor_dashboard'))

    def test_login_invalid_credentials(self):
        response = self.client.post(self.url, {'username': 'testuser', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_redirects_to_login(self):
        self.client.login(username='testuser', password='pass1234')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))


class PatientSignupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('patient_signup')
        self.valid_data = {
            'username': 'newpatient',
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'email': 'alice@example.com',
            'contact_number': '1234567890',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

    def test_signup_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_creates_user_and_patient(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        response = self.client.post(self.url, self.valid_data)
        self.assertTrue(User.objects.filter(username='newpatient').exists())
        self.assertTrue(Patient.objects.filter(user__username='newpatient').exists())

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_redirects_to_patient_dashboard(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        response = self.client.post(self.url, self.valid_data)
        self.assertRedirects(response, reverse('patient_dashboard'))

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_sends_welcome_email(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        self.client.post(self.url, self.valid_data)
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        self.assertIn('alice@example.com', call_args['to'])
        self.assertIn('Welcome', call_args['subject'])

    @patch('email_service.resend.Emails.send', side_effect=Exception('Resend API down'))
    def test_signup_succeeds_even_if_email_fails(self, mock_send):
        """Email failure must not prevent account creation."""
        response = self.client.post(self.url, self.valid_data)
        self.assertTrue(User.objects.filter(username='newpatient').exists())
        self.assertRedirects(response, reverse('patient_dashboard'))

    def test_invalid_signup_missing_fields(self):
        response = self.client.post(self.url, {'username': 'bad'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='bad').exists())

    def test_invalid_signup_password_mismatch(self):
        data = {**self.valid_data, 'password2': 'DifferentPass!'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newpatient').exists())


class DoctorSignupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('doctor_signup')
        self.valid_data = {
            'username': 'newdoctor',
            'first_name': 'Bob',
            'last_name': 'Builder',
            'email': 'bob@hospital.com',
            'department': 'Neurology',
            'degree': 'MD',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

    def test_signup_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_creates_user_and_doctor(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        self.client.post(self.url, self.valid_data)
        self.assertTrue(User.objects.filter(username='newdoctor').exists())
        self.assertTrue(Doctor.objects.filter(user__username='newdoctor').exists())

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_saves_department_and_degree(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        self.client.post(self.url, self.valid_data)
        doctor = Doctor.objects.get(user__username='newdoctor')
        self.assertEqual(doctor.department, 'Neurology')
        self.assertEqual(doctor.degree, 'MD')

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_redirects_to_doctor_dashboard(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        response = self.client.post(self.url, self.valid_data)
        self.assertRedirects(response, reverse('doctor_dashboard'))

    @patch('email_service.resend.Emails.send')
    def test_valid_signup_sends_welcome_email(self, mock_send):
        mock_send.return_value = {'id': 'fake-id'}
        self.client.post(self.url, self.valid_data)
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        self.assertIn('bob@hospital.com', call_args['to'])
        self.assertIn('Welcome', call_args['subject'])

    @patch('email_service.resend.Emails.send', side_effect=Exception('Resend API down'))
    def test_signup_succeeds_even_if_email_fails(self, mock_send):
        response = self.client.post(self.url, self.valid_data)
        self.assertTrue(User.objects.filter(username='newdoctor').exists())
        self.assertRedirects(response, reverse('doctor_dashboard'))

    def test_invalid_signup_missing_fields(self):
        response = self.client.post(self.url, {'username': 'baddoc'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baddoc').exists())
