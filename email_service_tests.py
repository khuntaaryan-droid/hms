"""
Tests for the email_service module.
Run with:  python manage.py test email_service_tests
"""
from unittest.mock import patch, call

from django.test import SimpleTestCase

import email_service


class BuildSignupWelcomeTest(SimpleTestCase):
    """Unit-tests for the internal _build_signup_welcome helper."""

    def test_subject_contains_welcome(self):
        subject, _ = email_service._build_signup_welcome('Alice')
        self.assertIn('Welcome', subject)

    def test_html_contains_patient_name(self):
        _, html = email_service._build_signup_welcome('Alice')
        self.assertIn('Alice', html)

    def test_html_contains_brand(self):
        _, html = email_service._build_signup_welcome('Alice')
        self.assertIn('Mini HMS', html)


class BuildBookingConfirmationTest(SimpleTestCase):
    """Unit-tests for the internal _build_booking_confirmation helper."""

    def _build(self):
        return email_service._build_booking_confirmation(
            patient_name='John',
            doctor_name='Smith',
            date='2026-05-01',
            time='10:00',
        )

    def test_subject_contains_confirmation(self):
        subject, _ = self._build()
        self.assertIn('Confirmation', subject)

    def test_html_contains_patient_name(self):
        _, html = self._build()
        self.assertIn('John', html)

    def test_html_contains_doctor_name(self):
        _, html = self._build()
        self.assertIn('Smith', html)

    def test_html_contains_date(self):
        _, html = self._build()
        self.assertIn('2026-05-01', html)

    def test_html_contains_time(self):
        _, html = self._build()
        self.assertIn('10:00', html)


class SendEmailTest(SimpleTestCase):
    """Integration-style tests for the public send_email() function."""

    @patch('email_service.resend.Emails.send')
    def test_signup_welcome_calls_resend(self, mock_send):
        mock_send.return_value = {'id': 'abc123'}
        email_service.send_email(
            action='SIGNUP_WELCOME',
            patient_email='alice@example.com',
            patient_name='Alice',
        )
        mock_send.assert_called_once()

    @patch('email_service.resend.Emails.send')
    def test_signup_welcome_sends_to_correct_address(self, mock_send):
        mock_send.return_value = {'id': 'abc123'}
        email_service.send_email(
            action='SIGNUP_WELCOME',
            patient_email='alice@example.com',
            patient_name='Alice',
        )
        params = mock_send.call_args[0][0]
        self.assertIn('alice@example.com', params['to'])

    @patch('email_service.resend.Emails.send')
    def test_booking_confirmation_calls_resend(self, mock_send):
        mock_send.return_value = {'id': 'def456'}
        email_service.send_email(
            action='BOOKING_CONFIRMATION',
            patient_email='john@example.com',
            patient_name='John',
            doctor_name='Smith',
            date='2026-05-01',
            time='10:00',
        )
        mock_send.assert_called_once()

    @patch('email_service.resend.Emails.send')
    def test_booking_confirmation_sends_to_correct_address(self, mock_send):
        mock_send.return_value = {'id': 'def456'}
        email_service.send_email(
            action='BOOKING_CONFIRMATION',
            patient_email='john@example.com',
            patient_name='John',
            doctor_name='Smith',
            date='2026-05-01',
            time='10:00',
        )
        params = mock_send.call_args[0][0]
        self.assertIn('john@example.com', params['to'])

    @patch('email_service.resend.Emails.send')
    def test_from_address_is_set(self, mock_send):
        mock_send.return_value = {'id': 'x'}
        email_service.send_email(
            action='SIGNUP_WELCOME',
            patient_email='test@example.com',
            patient_name='Test',
        )
        params = mock_send.call_args[0][0]
        self.assertIn('onboarding@resend.dev', params['from'])

    @patch('email_service.resend.Emails.send')
    def test_html_is_included_in_payload(self, mock_send):
        mock_send.return_value = {'id': 'x'}
        email_service.send_email(
            action='SIGNUP_WELCOME',
            patient_email='test@example.com',
            patient_name='Test',
        )
        params = mock_send.call_args[0][0]
        self.assertIn('html', params)
        self.assertTrue(len(params['html']) > 0)

    def test_invalid_action_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            email_service.send_email(
                action='UNKNOWN_ACTION',
                patient_email='x@y.com',
            )
        self.assertIn('UNKNOWN_ACTION', str(ctx.exception))

    @patch('email_service.resend.Emails.send')
    def test_returns_resend_response(self, mock_send):
        mock_send.return_value = {'id': 'resp-id'}
        result = email_service.send_email(
            action='SIGNUP_WELCOME',
            patient_email='test@example.com',
            patient_name='Test',
        )
        self.assertEqual(result, {'id': 'resp-id'})

    @patch('email_service.resend.Emails.send', side_effect=Exception('API error'))
    def test_resend_exception_propagates(self, mock_send):
        with self.assertRaises(Exception, msg='API error'):
            email_service.send_email(
                action='SIGNUP_WELCOME',
                patient_email='test@example.com',
                patient_name='Test',
            )
