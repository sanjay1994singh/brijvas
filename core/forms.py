from django import forms


class ContactForm(forms.Form):
    phone = forms.CharField(max_length=20, required=False)
    name = forms.CharField(
        max_length=100
    )

    email = forms.EmailField()

    subject = forms.CharField(
        max_length=255, required=False
    )

    message = forms.CharField(
        widget=forms.Textarea, max_length=5000
    )

    consent = forms.BooleanField(
        label='I agree to be contacted about this enquiry and have read the Privacy Policy.',
        required=True,
        error_messages={'required': 'Please agree to be contacted before sending your enquiry.'},
    )
