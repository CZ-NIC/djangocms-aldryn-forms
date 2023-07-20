import logging

from django.utils.translation import gettext_lazy as _

from .action_backends_base import BaseAction


logger = logging.getLogger(__name__)


class DefaultAction(BaseAction):
    verbose_name = _('Default')

    def form_valid(self, cmsplugin, instance, request, form):
        recipients = cmsplugin.send_notifications(instance, form)
        form.instance.set_recipients(recipients)
        form.save()
        cmsplugin.send_success_message(instance, request)


class EmailAction(BaseAction):
    verbose_name = _('Email only')

    def form_valid(self, cmsplugin, instance, request, form):
        recipients = cmsplugin.send_notifications(instance, form)
        logger.info(f'Sent email notifications to {len(recipients)} recipients.')
        cmsplugin.send_success_message(instance, request)


class NoAction(BaseAction):
    verbose_name = _('None')

    def form_valid(self, cmsplugin, instance, request, form):
        form_id = form.form_plugin.id
        logger.info(f'Not persisting data for "{form_id}" since action_backend is set to "none"')
