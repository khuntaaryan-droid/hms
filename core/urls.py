from django.urls import path
from . import views

urlpatterns = [
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),

    path('book/<int:slot_id>/', views.book_appointment, name='book_appointment'),
    path('google/authorize/', views.google_authorize, name='google_authorize'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('google/process/', views.process_google_booking, name='process_google_booking'),
]
