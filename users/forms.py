# users/forms.py (пример, должен быть у тебя)
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=False, label='Имя')
    email = forms.EmailField(required=False, label='Email')
    accept_terms = forms.BooleanField(
        required=True,
        label=(
            'Я принимаю '
            '<a href="/terms/" target="_blank">Пользовательское соглашение</a> '
            'и <a href="/privacy/" target="_blank">Политику конфиденциальности</a>'
        )
    )
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Пользователь с таким именем уже существует.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким email уже существует.')
        return email

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'email')
        labels = {'username': 'Логин', 'first_name': 'Имя', 'email': 'Email'}

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if username and qs.exists():
            raise ValidationError('Данный логин уже занят.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Данный email уже используется.')
        return email

