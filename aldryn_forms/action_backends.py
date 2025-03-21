import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .action_backends_base import BaseAction
from .api.webhook import trigger_webhooks
from .constants import ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION


if TYPE_CHECKING:  # pragma: no cover
    from .cms_plugins import FormPlugin as CMSFormPlugin
    from .forms import FormSubmissionBaseForm
    from .models import FormPlugin


logger = logging.getLogger(__name__)


class DefaultAction(BaseAction):
    verbose_name = _('Save to site administration and send email')

    def form_valid(
        self,
        cmsplugin: "CMSFormPlugin",
        instance: "FormPlugin",
        request: HttpRequest,
        form: "FormSubmissionBaseForm"
    ) -> None:
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            recipients = cmsplugin.postpone_send_notifications(instance, form)
        elif not form.instance.honeypot_filled:
            recipients = cmsplugin.send_notifications(instance, form)
        if not form.instance.honeypot_filled:
            form.instance.set_recipients(recipients)
            form.save()
            if not duration:
                site = Site.objects.first()
                trigger_webhooks(instance.webhooks, form.instance, site.domain)
        cmsplugin.send_success_message(instance, request)


class EmailAction(BaseAction):
    verbose_name = _('Only send email')

    def form_valid(
        self,
        cmsplugin: "CMSFormPlugin",
        instance: "FormPlugin",
        request: HttpRequest,
        form: "FormSubmissionBaseForm"
    ) -> None:
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            recipients = cmsplugin.postpone_send_notifications(instance, form)
        elif not form.instance.honeypot_filled:
            recipients = cmsplugin.send_notifications(instance, form)
            logger.info(f'Sent email notifications to {len(recipients)} recipients.')
            site = Site.objects.first()
            trigger_webhooks(instance.webhooks, form.instance, site.domain)
        cmsplugin.send_success_message(instance, request)


class NoAction(BaseAction):
    verbose_name = _('No action')

    def form_valid(
        self,
        cmsplugin: "CMSFormPlugin",
        instance: "FormPlugin",
        request: HttpRequest,
        form: "FormSubmissionBaseForm"
    ) -> None:
        form_id = form.form_plugin.id
        logger.info(f'Not persisting data for "{form_id}" since action_backend is set to "none"')
