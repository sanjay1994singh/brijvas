from django.db.models import FileField
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver


def _file_fields(model):
    return [
        field
        for field in model._meta.get_fields()
        if isinstance(field, FileField)
    ]


def _delete_file(file_field):
    if file_field and getattr(file_field, "name", ""):
        file_field.delete(save=False)


@receiver(post_delete)
def delete_files_on_model_delete(sender, instance, **kwargs):
    if not hasattr(instance, "_meta"):
        return

    for field in _file_fields(sender):
        _delete_file(getattr(instance, field.name, None))


@receiver(pre_save)
def delete_replaced_files_on_model_save(sender, instance, **kwargs):
    if not hasattr(instance, "_meta") or not instance.pk:
        return

    fields = _file_fields(sender)

    if not fields:
        return

    try:
        old_instance = sender._default_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    for field in fields:
        old_file = getattr(old_instance, field.name, None)
        new_file = getattr(instance, field.name, None)

        if (
            old_file
            and getattr(old_file, "name", "")
            and getattr(old_file, "name", "") != getattr(new_file, "name", "")
        ):
            _delete_file(old_file)
