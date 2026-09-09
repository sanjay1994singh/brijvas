from django.urls import path
from .uploads import editor_upload
urlpatterns = [path('image_upload/', editor_upload, name='ck_editor_5_upload_file')]

