from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django.core.exceptions import ValidationError

class SignUpForm(UserCreationForm):
    full_name = forms.CharField(max_length=100, help_text='Enter your full name')
    email = forms.EmailField(max_length=150, required=False, help_text='Email (optional)')
    mobile = forms.CharField(max_length=15, help_text='Enter your mobile number')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email == '':
            return None
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Custom user with this Email address already exists.")
        return email

    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'mobile', 'password1', 'password2')