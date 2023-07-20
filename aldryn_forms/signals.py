from django.db.models.signals import pre_delete
from django.dispatch import Signal, receiver

from .models import EmailFieldPlugin


form_pre_save = Signal()
form_post_save = Signal()


@receiver(pre_delete, sender=EmailFieldPlugin, dispatch_uid='aldryn_forms_pre_delete_field')
def protect_form_action_backend(sender, instance, using, **kwargs):
    plugin_form, action_backend = instance.get_parent_form_action_backend()
    if action_backend is not None:
        getattr(action_backend, "delete_field", lambda field, form: None)(instance, plugin_form)
