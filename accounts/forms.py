from django import forms
from django.contrib.auth import get_user_model
from .locations import INDIAN_STATES
from .username_utils import suggest_usernames, username_exists, validate_username

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

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()

        if username and not validate_username(username):
            raise forms.ValidationError(
                "Username can contain only letters, numbers and @/./+/-/_."
            )

        if username and username_exists(username):
            suggestions = ", ".join(suggest_usernames(username))
            raise forms.ValidationError(
                f"This username is already taken. Try: {suggestions}."
            )

        return username

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
            'address',
            'city',
            'state',
            'user_type',
            'profile_image'

        )

        widgets = {
            'first_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'last_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'email': forms.EmailInput(
                attrs={'class': 'form-control'}
            ),
            'phone': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'address': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),
            'city': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'state': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'list': 'state-list',
                    'autocomplete': 'address-level1'
                }
            ),
            'user_type': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'profile_image': forms.ClearableFileInput(
                attrs={'class': 'form-control'}
            ),
        }

    state_options = INDIAN_STATES

    def clean_state(self):
        state = (self.cleaned_data.get("state") or "").strip()

        if not state:
            return state

        valid_states = {item.casefold(): item for item in INDIAN_STATES}
        normalized_state = valid_states.get(state.casefold())

        if not normalized_state:
            raise forms.ValidationError(
                "Please select a valid Indian state from the suggestions."
            )

        return normalized_state

    def save(self, commit=True):
        user = super().save(commit=False)
        user.country = "India"

        if user.pk:
            old_user = User.objects.only(
                "user_type",
                "is_verified"
            ).get(pk=user.pk)

            if (
                old_user.user_type != user.user_type
                and user.user_type in ("owner", "agent")
            ):
                user.is_verified = False

            if user.user_type == "buyer":
                user.is_verified = False

        if commit:
            user.save()

        return user
