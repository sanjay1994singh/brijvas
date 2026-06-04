from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput()
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput()
    )

    class Meta:

        model = User

        fields = (

            'first_name',
            'last_name',
            'username',
            'email',
            'phone',
            'user_type'

        )

    def clean(self):

        cleaned_data = super().clean()

        password1 = cleaned_data.get('password1')

        password2 = cleaned_data.get('password2')

        if password1 != password2:
            raise forms.ValidationError(
                "Passwords do not match"
            )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(commit=False)

        user.set_password(
            self.cleaned_data['password1']
        )

        if commit:
            user.save()

        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User

        fields = (

            'first_name',
            'last_name',
            'email',
            'phone',
            'profile_image'

        )
