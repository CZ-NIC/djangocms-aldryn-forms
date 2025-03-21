from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.utils.timezone import now as django_timezone_now
from django.utils.timezone import timedelta

from aldryn_forms.api.webhook import trigger_webhooks
from aldryn_forms.constants import ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION
from aldryn_forms.models import SubmittedToBeSent
from aldryn_forms.utils import send_postponed_notifications


class Command(BaseCommand):
    help = "Send postponed emails."

    def handle(self, *args, **options):
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            expire = django_timezone_now() - timedelta(minutes=duration)
            queryset = SubmittedToBeSent.objects.filter(sent_at__lt=expire)
        else:
            queryset = SubmittedToBeSent.objects.all()

        site = Site.objects.first()
        for instance in queryset:
            if not instance.honeypot_filled:
                if send_postponed_notifications(instance):
                    trigger_webhooks(instance.webhooks, instance, site.domain)
            instance.delete()
