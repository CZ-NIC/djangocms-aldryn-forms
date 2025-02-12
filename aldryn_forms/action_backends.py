import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .action_backends_base import BaseAction
from .constants import ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION


logger = logging.getLogger(__name__)


class DefaultAction(BaseAction):
    verbose_name = _('Save to site administration and send email')

    def form_valid(self, cmsplugin, instance, request, form):
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            recipients = cmsplugin.postpone_send_notifications(instance, form)
        else:
            recipients = cmsplugin.send_notifications(instance, form)
        form.instance.set_recipients(recipients)
        form.save()
        cmsplugin.send_success_message(instance, request)


class EmailAction(BaseAction):
    verbose_name = _('Only send email')

    def form_valid(self, cmsplugin, instance, request, form):
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            recipients = cmsplugin.postpone_send_notifications(instance, form)
            logger.info(f'Pospone sent email notifications to {len(recipients)} recipients.')
        else:
            recipients = cmsplugin.send_notifications(instance, form)
            logger.info(f'Sent email notifications to {len(recipients)} recipients.')
        cmsplugin.send_success_message(instance, request)


class NoAction(BaseAction):
    verbose_name = _('No action')

    def form_valid(self, cmsplugin, instance, request, form):
        form_id = form.form_plugin.id
        logger.info(f'Not persisting data for "{form_id}" since action_backend is set to "none"')
