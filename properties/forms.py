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
            'title',
            'slug',
            'address',
            'area_sqft',
            'area_gaj',
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "price": "Property price",
            "area": "Area size",
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

    def save(self, commit=True):
        property_obj = super().save(commit=False)
        property_obj.title = ""
        property_obj.address = ""

        if commit:
            property_obj.save()
            self.save_m2m()

        return property_obj


class PropertyGalleryForm(forms.ModelForm):
    class Meta:
        model = PropertyGallery

        fields = ['image']
