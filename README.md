# Mini Hospital Management System (HMS)

A full-stack, dual-dashboard Hospital Management System built with **Django**, featuring Google Calendar synchronization and automated transactional email notifications powered by the **Resend Python SDK** 

---

## 🌟 Features

- **Dual Dashboards** — Role-based interfaces for Doctors and Patients.
- **Smart Scheduling** — Doctors generate hourly time slots; booked slots are instantly removed from the available pool.
- **Google Calendar Integration** — Secure OAuth2 + PKCE flow automatically creates Google Calendar events for both parties on booking.
- **Transactional Emails** — Welcome and appointment confirmation emails sent directly via the Resend Python SDK, integrated natively into Django.
- **Comprehensive Test Suite** — 75 automated tests covering models, views, and the email service (zero external dependencies during tests).

---

## 🛠️ Prerequisites

Ensure you have the following before starting:

- **Python 3.10+**
- **PostgreSQL** (or SQLite for development/testing)
- **Google Cloud Console Account** — for Calendar API `credentials.json`
- **Resend Account** — for your API key ([resend.com](https://resend.com))


---

## 📂 Project Structure

```
hms/
├── manage.py
├── credentials.json          # Google OAuth keys (user-provided)
├── email_service.py          # Resend email utility (Python)
├── email_service_tests.py    # Tests for the email module
├── requirements.txt
│
├── hms/                      # Django project settings
│   ├── settings.py
│   └── test_settings.py      # SQLite override for running tests
│
├── accounts/                 # Auth: Patient & Doctor signup/login
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   └── tests.py
│
└── core/                     # Main logic: slots, appointments, calendar
    ├── models.py
    ├── views.py
    ├── urls.py
    └── tests.py
```

---

## 🚀 Setup & Installation

### Step 1: Create and Activate Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 3: Configure the Database

The project uses **PostgreSQL** by default. Update `hms/settings.py` with your credentials:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'hms_database',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then apply migrations:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Step 4: Configure Google Calendar API

1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Enable the **Google Calendar API**.
3. Create an **External OAuth Consent Screen** and add your Gmail to **Test Users**.
4. Create **OAuth Client ID** credentials (Web Application) with redirect URI:
   ```
   http://127.0.0.1:8000/oauth2callback/
   ```
5. Download the JSON file, rename it to `credentials.json`, and place it in the project root.

### Step 5: Set Your Resend API Key

```powershell
# PowerShell (current session only)
$env:RESEND_API_KEY = "re_your_key_here"
```

> To persist across sessions, add it to your system environment variables or a `.env` file.

---

## 🏃‍♂️ Running the Application

Only **one terminal** is needed now:

```powershell
$env:RESEND_API_KEY = "re_your_key_here"
.\.venv\Scripts\activate
python manage.py runserver
```

Then open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🧪 Running Tests

Tests use SQLite so **no database server is required**:

```powershell
# Run all tests
.\.venv\Scripts\python manage.py test accounts core email_service_tests --settings=hms.test_settings

# Run a specific module
.\.venv\Scripts\python manage.py test email_service_tests --settings=hms.test_settings

# Verbose output
.\.venv\Scripts\python manage.py test accounts core email_service_tests --settings=hms.test_settings --verbosity=2
```

### Test Coverage

| Module | Tests | What's covered |
|---|---|---|
| `accounts/tests.py` | 27 | `Doctor`/`Patient` models, login, logout, patient signup, doctor signup |
| `core/tests.py` | 33 | `TimeSlot`/`Appointment` models, doctor dashboard, patient dashboard, booking flow |
| `email_service_tests.py` | 15 | `send_email()`, HTML builders, error propagation, invalid actions |
| **Total** | **75** | **All passing ✅** |

> All Resend and Google Calendar API calls are mocked — tests run fully offline.

---

## 🔄 Booking Flow

1. Patient visits the dashboard and selects an available slot.
2. If not yet authorized, they are redirected to Google OAuth.
3. On approval, the slot is booked and marked as unavailable.
4. A Google Calendar event is created for the doctor.
5. A confirmation email is sent to the patient via Resend.

---

## 📧 Email Actions

The `email_service.py` module supports two transactional email types:

| Action | Trigger | Recipient |
|---|---|---|
| `SIGNUP_WELCOME` | Patient or Doctor registers | New user |
| `BOOKING_CONFIRMATION` | Appointment is confirmed | Patient |
