from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now as django_timezone_now
from django.utils.timezone import timedelta

from aldryn_forms.constants import ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION
from aldryn_forms.models import SubmittedToBeSent
from aldryn_forms.utils import send_notifications
from aldryn_forms.cms_plugins import FormPlugin


class Command(BaseCommand):
    help = "Send postponed emails."

    def handle(self, *args, **options):
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            expire = django_timezone_now() - timedelta(minutes=duration)
            print("expire:", expire)
            cmsplugin = FormPlugin()
            print("cmsplugin:", cmsplugin)
            for instance in SubmittedToBeSent.objects.filter(sent_at__lt=expire):
                print(instance.sent_at)
                form_class = cmsplugin.get_form_class(instance)
                print("form_class:", form_class)
                # form = None
                # send_notifications(instance, form)
