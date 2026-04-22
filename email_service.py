import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")


def _build_signup_welcome(patient_name: str) -> tuple[str, str]:
    subject = "Welcome to Mini HMS!"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
        <h2 style="color: #0050b3;">Welcome to Mini HMS, {patient_name}!</h2>
        <p>Your account has been successfully created.</p>
        <p>You can now log in to your dashboard and manage your healthcare journey with ease.</p>
        <br>
        <p>Stay healthy,</p>
        <p><strong>The Mini-HMS Team</strong></p>
    </div>
    """
    return subject, html


def _build_booking_confirmation(patient_name: str, doctor_name: str, date: str, time: str) -> tuple[str, str]:
    subject = "Appointment Confirmation - Mini HMS"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
        <h2 style="color: #0050b3;">Hello {patient_name},</h2>
        <p>Your appointment has been successfully confirmed.</p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
            <p><strong>Doctor:</strong> Dr. {doctor_name}</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>Time:</strong> {time}</p>
        </div>
        <br>
        <p>Thank you for choosing Mini-HMS.</p>
    </div>
    """
    return subject, html


def send_email(action: str, patient_email: str, **kwargs) -> dict:
    if action == "SIGNUP_WELCOME":
        subject, html = _build_signup_welcome(kwargs["patient_name"])
    elif action == "BOOKING_CONFIRMATION":
        subject, html = _build_booking_confirmation(
            kwargs["patient_name"],
            kwargs["doctor_name"],
            kwargs["date"],
            kwargs["time"],
        )
    else:
        raise ValueError(f"Invalid action '{action}'. Must be SIGNUP_WELCOME or BOOKING_CONFIRMATION.")

    params: resend.Emails.SendParams = {
        "from": "HMS Admin <onboarding@resend.dev>",
        "to": [patient_email],
        "subject": subject,
        "html": html,
    }
    return resend.Emails.send(params)
