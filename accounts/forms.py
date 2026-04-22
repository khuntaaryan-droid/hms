from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class PatientSignUpForm(UserCreationForm):
    # Add the fields we want to require for the User model
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    # Add the fields for our custom Patient profile
    contact_number = forms.CharField(max_length=15, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        # 'username' is required by default, we append our new fields to it
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')


class DoctorSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)

    # Add the fields for our custom Doctor profile
    department = forms.CharField(max_length=100, required=True)
    degree = forms.CharField(max_length=50, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

