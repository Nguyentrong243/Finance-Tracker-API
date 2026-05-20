from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import password_validation

from .models import UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'input-field'})
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Họ', 'class': 'input-field'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Tên', 'class': 'input-field'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Tên đăng nhập', 'class': 'input-field'}),
            'password1': forms.PasswordInput(attrs={'placeholder': 'Mật khẩu', 'class': 'input-field'}),
            'password2': forms.PasswordInput(attrs={'placeholder': 'Xác nhận mật khẩu', 'class': 'input-field'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class AccountSettingsForm(forms.ModelForm):
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Số điện thoại', 'class': 'input-field'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Họ', 'class': 'input-field'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Tên', 'class': 'input-field'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'input-field'}),
        }


class SecuritySettingsForm(forms.Form):
    two_factor_enabled = forms.BooleanField(required=False)
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mật khẩu mới', 'class': 'input-field'})
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Xác nhận mật khẩu mới', 'class': 'input-field'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError('Mật khẩu mới và xác nhận mật khẩu phải giống nhau.')
            password_validation.validate_password(password1)

        return cleaned_data


class AppSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'theme_mode',
            'currency',
            'date_format',
        ]
        widgets = {
            'theme_mode': forms.Select(attrs={'class': 'input-field'}),
            'currency': forms.Select(attrs={'class': 'input-field'}),
            'date_format': forms.Select(attrs={'class': 'input-field'}),
        }


class TwoFactorAuthenticationForm(AuthenticationForm):
    captcha_code = forms.CharField(
        required=False,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'off',
                'placeholder': 'Mã xác thực',
                'class': 'input-field',
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()

        if user is not None:
            profile = getattr(user, 'userprofile', None)
            if profile is None:
                profile = UserProfile.objects.filter(user=user).first()
            if profile and profile.two_factor_enabled:
                captcha_code = cleaned_data.get('captcha_code', '').strip().upper()
                session_code = self.request.session.get('login_2fa_code', '')
                if not captcha_code:
                    raise forms.ValidationError('Vui lòng nhập mã xác thực 2FA.')
                if captcha_code != session_code:
                    raise forms.ValidationError('Mã xác thực 2FA không chính xác.')

        return cleaned_data
