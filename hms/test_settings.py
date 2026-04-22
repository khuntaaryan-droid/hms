"""
Test-only settings — overrides the production database with SQLite
so tests can run without a running PostgreSQL server.

Usage:
    python manage.py test --settings=hms.test_settings accounts core email_service_tests
"""
from .settings import *   # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

# Silence all application loggers during tests so output stays clean.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {'class': 'logging.NullHandler'},
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}
