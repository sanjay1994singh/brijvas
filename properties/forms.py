from django import forms
from django.db.models import Q
from django_ckeditor_5.widgets import CKEditor5Widget
from accounts.locations import INDIAN_STATES
from locations.models import City, District, State
from .models import Property, PropertyGallery


class PropertyForm(forms.ModelForm):
    CHECKBOX_FIELDS = {
        "is_featured",
        "is_active",
    }

    class Meta:
        model = Property

        exclude = (
            'user',
            'tenant',
            'title',
            'slug',
            'area_sqft',
            'area_gaj',
            'area_sq_meter',
            'area_acre',
            'area_bigha',
            'bedrooms',
            'bathrooms',
            'parking',
            'furnishing',
            'latitude',
            'longitude',
            'views',
            'is_featured',
            'is_verified',
            'is_active',
            'created_at',
            'updated_at',
        )

        widgets = {

            'price': forms.NumberInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'area': forms.NumberInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'description': CKEditor5Widget(
                config_name='extends',
                attrs={
                    'class': 'django_ckeditor_5'
                }
            ),

            'address': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Full property address'
                }
            ),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.instance.tenant = tenant
        from .models import PropertyType
        property_type_queryset = PropertyType.objects.filter(tenant__isnull=True)
        if self.instance and self.instance.property_type_id:
            property_type_queryset = PropertyType.objects.filter(
                Q(tenant__isnull=True) | Q(pk=self.instance.property_type_id)
            )
        self.fields['property_type'].queryset = property_type_queryset.order_by('name')
        self.fields['property_type'].empty_label = "Select property type"
        self.fields['purpose'].choices = [("", "Select purpose")] + list(Property.PURPOSE_CHOICES)
        for state_name in INDIAN_STATES:
            State.objects.get_or_create(name=state_name, defaults={'tenant': None})
        self.fields['state'].queryset = State.objects.filter(tenant__isnull=True).order_by('name')
        district_queryset = District.objects.none()
        city_queryset = City.objects.none()
        state_id = self.data.get('state') or getattr(self.instance, 'state_id', None)
        district_id = self.data.get('district') or getattr(self.instance, 'district_id', None)
        if tenant and state_id:
            district_queryset = District.objects.filter(tenant=tenant, state_id=state_id).order_by('name')
            city_queryset = City.objects.filter(tenant=tenant, state_id=state_id).order_by('name')
        if tenant and district_id:
            city_queryset = city_queryset.filter(district_id=district_id)
        self.fields['district'].queryset = district_queryset
        self.fields['district'].required = True
        self.fields['city'].queryset = city_queryset
        self.fields['price'].required = False
        self.fields['state'].empty_label = "Select state"
        self.fields['district'].empty_label = "Select district"
        self.fields['city'].empty_label = "Select city"

        placeholders = {
            "price": "Property price",
            "area": "Area size",
            "street": "Street, road or locality",
            "building_apartment": "Building, apartment or landmark",
        }

        for name, field in self.fields.items():
            widget = field.widget

            if name in self.CHECKBOX_FIELDS:
                widget.attrs["class"] = "form-check-input"
                continue

            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "form-control"
            elif not isinstance(widget, CKEditor5Widget):
                widget.attrs["class"] = "form-control"

            if name in placeholders:
                widget.attrs["placeholder"] = placeholders[name]

        self.fields["featured_image"].help_text = (
            "Image optional hai. Upload karne par quality maintain rakhte hue file automatically lagbhag 1 MB ke andar optimize hogi."
        )
        self.fields["featured_image"].required = False
        self.fields["featured_image"].widget.attrs["accept"] = "image/*"

    def clean(self):
        data = super().clean()
        if data.get('district') and data.get('state') and data['district'].state_id != data['state'].pk:
            self.add_error('district', 'Select a district in the selected state.')
        if data.get('district') and data.get('city') and data['city'].district_id != data['district'].pk:
            self.add_error('city', 'Select a city in the selected district.')
        if data.get('city') and data.get('state') and data['city'].state_id != data['state'].pk:
            self.add_error('city', 'Select a city in the selected state.')
        if self.tenant and data.get('district') and data['district'].tenant_id != self.tenant.pk:
            self.add_error('district', 'Select a district for this website.')
        if self.tenant and data.get('city') and data['city'].tenant_id != self.tenant.pk:
            self.add_error('city', 'Select a city for this website.')
        image = data.get('featured_image')
        if image and getattr(image, 'size', 0) > 20 * 1024 * 1024:
            self.add_error('featured_image', 'Upload image up to 20 MB. Save ke baad quality maintain rakhte hue image lagbhag 1 MB ke andar optimize hogi.')
        if data.get('description'):
            from saas.uploads import sanitize_html
            data['description'] = sanitize_html(data['description'])
        return data

    def save(self, commit=True):
        property_obj = super().save(commit=False)
        property_obj.title = ""

        if commit:
            property_obj.save()
            self.save_m2m()

        return property_obj


class PropertyGalleryForm(forms.ModelForm):
    class Meta:
        model = PropertyGallery

        fields = ['image']
