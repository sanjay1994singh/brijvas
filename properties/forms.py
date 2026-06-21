from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Property, PropertyGallery


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property

        exclude = (
            'user',
            'slug',
            'views',
            'is_verified',
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


class PropertyGalleryForm(forms.ModelForm):
    class Meta:
        model = PropertyGallery

        fields = ['image']
