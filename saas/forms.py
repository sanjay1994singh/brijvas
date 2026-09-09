import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from core.models import SiteSetting
from .models import Plan
from .services import validate_slug, validate_domain_for_tenant


class SignupForm(UserCreationForm):
    business_name = forms.CharField(max_length=160)
    site_slug = forms.CharField(max_length=48, help_text='Your unique website address, for example sunrise-realty.')
    email = forms.EmailField(required=True)
    plan = forms.ModelChoiceField(queryset=Plan.objects.none(), empty_label=None)

    class Meta:
        model = get_user_model()
        fields = ('business_name', 'site_slug', 'username', 'email', 'phone', 'plan', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = Plan.objects.filter(is_active=True).order_by('listing_limit')

    def clean_site_slug(self):
        return validate_slug(self.cleaned_data['site_slug'])

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please sign in.')
        return email


class SiteForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = ('site_name', 'tagline', 'about_text', 'logo', 'favicon', 'email', 'phone', 'whatsapp', 'address', 'facebook', 'instagram', 'youtube', 'primary_color')
        widgets = {'primary_color': forms.TextInput(attrs={'type': 'color'}), 'about_text': forms.Textarea(attrs={'rows': 4}), 'address': forms.Textarea(attrs={'rows': 2})}

    def clean_primary_color(self):
        color = self.cleaned_data['primary_color']
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise forms.ValidationError('Use a six-digit hex color.')
        return color

    def clean_whatsapp(self):
        value = self.cleaned_data['whatsapp']
        if value and not re.fullmatch(r'\+?[0-9]{7,15}', value):
            raise forms.ValidationError('Use an international phone number with digits only.')
        return value.lstrip('+')

    def clean(self):
        data = super().clean()
        for key in ('logo', 'favicon'):
            file = data.get(key)
            if file and getattr(file, 'size', 0) > 2 * 1024 * 1024:
                self.add_error(key, 'Maximum size is 2 MB.')
            if file and hasattr(file, 'image') and file.image.format not in ('JPEG', 'PNG', 'WEBP', 'ICO'):
                self.add_error(key, 'Use a JPEG, PNG, WebP or ICO image.')
        return data


class DomainForm(forms.Form):
    hostname = forms.CharField(max_length=253)

    def clean_hostname(self):
        return validate_domain_for_tenant(self.cleaned_data['hostname'])


class MemberForm(forms.Form):
    username = forms.CharField(max_length=150, help_text='An existing registered account username.')
    role = forms.ChoiceField(choices=[('admin', 'Business admin'), ('agent', 'Agent')])
