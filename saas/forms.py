import re
from django import forms
from django.contrib.auth import get_user_model
from accounts.locations import INDIAN_STATES
from accounts.phone_utils import indian_whatsapp_number, normalize_indian_mobile
from core.models import SiteSetting
from .models import Plan
from .services import allocate_business_slug, validate_domain_for_tenant


class SignupForm(forms.ModelForm):
    business_name = forms.CharField(max_length=160, label='Business / brand name', help_text='Your website address is created automatically from this name. Example: Sharma Realty becomes sharmarealty. If taken, a number is added.')
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=True, max_length=20, label='Mobile number')
    state = forms.ChoiceField(choices=[('', 'Select state')] + [(state, state) for state in INDIAN_STATES], required=False)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='Confirm password', widget=forms.PasswordInput)
    plan = forms.ModelChoiceField(queryset=Plan.objects.none(), empty_label=None)
    accepted_purchase_terms = forms.BooleanField(
        label='I have read and agree to the plan purchase terms.',
        required=True,
        error_messages={'required': 'Please read and accept the plan purchase terms to continue.'},
    )

    class Meta:
        model = get_user_model()
        fields = ('email', 'phone', 'state')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = Plan.objects.filter(is_active=True).order_by('listing_limit')
        self.order_fields([
            'business_name',
            'email',
            'phone',
            'state',
            'password',
            'confirm_password',
            'plan',
            'accepted_purchase_terms',
        ])

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        return email

    def clean_phone(self):
        try:
            phone = normalize_indian_mobile(self.cleaned_data['phone'])
        except ValueError as exc:
            raise forms.ValidationError(str(exc))
        return phone

    def clean(self):
        data = super().clean()
        business_name = (data.get('business_name') or '').strip()
        if business_name:
            data['username'] = allocate_business_slug(business_name)
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.state = self.cleaned_data['state']
        user.country = 'India'
        user.user_type = 'owner'
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class SiteForm(forms.ModelForm):
    state = forms.ChoiceField(choices=[('', 'Select state')] + [(state, state) for state in INDIAN_STATES], required=False)

    class Meta:
        model = SiteSetting
        fields = ('site_name', 'tagline', 'about_text', 'logo', 'favicon', 'email', 'phone', 'whatsapp', 'state', 'address', 'facebook', 'instagram', 'youtube', 'primary_color', 'google_analytics_id', 'google_ads_id', 'google_site_verification', 'custom_head_scripts')
        widgets = {'primary_color': forms.TextInput(attrs={'type': 'color'}), 'about_text': forms.Textarea(attrs={'rows': 4}), 'address': forms.Textarea(attrs={'rows': 2}), 'custom_head_scripts': forms.Textarea(attrs={'rows': 5})}

        labels = {
            'google_analytics_id': 'Google Analytics measurement ID',
            'google_ads_id': 'Google Ads tag ID',
            'google_site_verification': 'Google site verification code',
            'custom_head_scripts': 'Extra head scripts',
        }

        help_texts = {
            'google_analytics_id': 'Example: G-XXXXXXXXXX',
            'google_ads_id': 'Example: AW-123456789',
            'google_site_verification': 'Paste only the content value from the Google verification meta tag.',
            'custom_head_scripts': 'Optional. Paste trusted Google/ads scripts that must appear inside the public site head.',
        }

    def clean_primary_color(self):
        color = self.cleaned_data['primary_color']
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise forms.ValidationError('Use a six-digit hex color.')
        return color

    def clean_whatsapp(self):
        value = self.cleaned_data['whatsapp']
        if value:
            try:
                return indian_whatsapp_number(value)
            except ValueError as exc:
                raise forms.ValidationError(str(exc))
        return value

    def clean_phone(self):
        value = self.cleaned_data['phone']
        if value:
            try:
                return normalize_indian_mobile(value)
            except ValueError as exc:
                raise forms.ValidationError(str(exc))
        return value

    def clean_google_analytics_id(self):
        value = (self.cleaned_data.get('google_analytics_id') or '').strip()
        if value and not re.fullmatch(r'G-[A-Za-z0-9]+', value):
            raise forms.ValidationError('Use a valid Google Analytics ID, like G-XXXXXXXXXX.')
        return value.upper()

    def clean_google_ads_id(self):
        value = (self.cleaned_data.get('google_ads_id') or '').strip()
        if value and not re.fullmatch(r'AW-[0-9]+', value):
            raise forms.ValidationError('Use a valid Google Ads ID, like AW-123456789.')
        return value.upper()

    def clean_google_site_verification(self):
        return (self.cleaned_data.get('google_site_verification') or '').strip()

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
