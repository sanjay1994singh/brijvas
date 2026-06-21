from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
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
            'slug',
            'views',
            'is_featured',
            'is_verified',
            'is_active',
            'created_at',
            'updated_at',
        )

        widgets = {

            'title': forms.TextInput(
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

            'address': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "title": "Example: 250 Gaj premium plot in Vrindavan",
            "address": "Full property address or nearby landmark",
            "price": "Property price",
            "area": "Area size",
            "area_unit": "sqft, gaj, acre...",
            "bedrooms": "0",
            "bathrooms": "0",
            "parking": "0",
            "furnishing": "Semi furnished, furnished, unfurnished...",
            "latitude": "Optional latitude",
            "longitude": "Optional longitude",
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
            "Upload a clear front image. It will be compressed automatically."
        )


class PropertyGalleryForm(forms.ModelForm):
    class Meta:
        model = PropertyGallery

        fields = ['image']
