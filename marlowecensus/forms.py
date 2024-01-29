from django import forms
from django.contrib import auth
from django.contrib.auth.forms import UserCreationForm
from .models import *
from django.forms import inlineformset_factory, TextInput, formset_factory
import datetime


class LoginForm(forms.ModelForm):
    error_messages = {'password_mismatch': "The two password fields didn't "
                      "match. Please enter both fields again.",
                      }
    password1 = forms.CharField(widget=forms.PasswordInput,
                                max_length=50,
                                min_length=6,
                                label='Password',
                                )
    password2 = forms.CharField(widget=forms.PasswordInput,
                                max_length=50,
                                min_length=6,
                                label='Password Confirmation',
                                help_text="\n Enter the same password as"
                                " above, for verification.",
                                )
    email = forms.CharField(max_length=75,
                            required=True
                            )

    class Meta:
        model = auth.get_user_model()
        fields = ['username',
                  'first_name',
                  'last_name',
                  'email',
                  'password1',
                  'password2']

    # raise an error if the entered password1 and password2 are mismatched
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return self.cleaned_data

    # raise an error if email is already taken
    def clean_email(self):
        data = self.cleaned_data['email']
        if User.objects.filter(email=data).exists():
            raise forms.ValidationError("This email is already used.")
        return data
