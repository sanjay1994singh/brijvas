"""Delete only unreferenced files after a successful database transaction."""
from django.apps import apps
from django.db import transaction
from django.db.models import FileField
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver


def _fields(model):
    return [field for field in model._meta.fields if isinstance(field, FileField)]


def _schedule_delete(file, using):
    if not file or not file.name:
        return
    name, storage = file.name, file.storage
    def delete_if_unused():
        for model in apps.get_models():
            for field in _fields(model):
                if model._default_manager.using(using).filter(**{field.name: name}).exists():
                    return
        storage.delete(name)
    transaction.on_commit(delete_if_unused, using=using)


@receiver(post_delete)
def delete_files_on_model_delete(sender, instance, using, **kwargs):
    for field in _fields(sender):
        _schedule_delete(getattr(instance, field.name, None), using)


@receiver(pre_save)
def delete_replaced_files_on_model_save(sender, instance, using, raw=False, **kwargs):
    if raw or not instance.pk or not _fields(sender):
        return
    old = sender._default_manager.using(using).filter(pk=instance.pk).first()
    if not old:
        return
    for field in _fields(sender):
        previous, current = getattr(old, field.name), getattr(instance, field.name)
        if previous and previous.name != getattr(current, 'name', ''):
            _schedule_delete(previous, using)
