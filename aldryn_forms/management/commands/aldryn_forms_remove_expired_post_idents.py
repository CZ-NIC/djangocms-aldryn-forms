from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now as django_timezone_now
from django.utils.timezone import timedelta

from aldryn_forms.constants import ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION
from aldryn_forms.models import FormSubmission


class Command(BaseCommand):
    help = "Remove expired post idents."

    def handle(self, *args, **options):
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration:
            expire = django_timezone_now() - timedelta(minutes=duration)
            FormSubmission.objects.filter(
                post_ident__isnull=False, sent_at__lt=expire
            ).update(post_ident=None)
            FormSubmission.objects.filter(post_ident__isnull=True, honeypot_filled=True).delete()
