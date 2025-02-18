from django.core.management.base import BaseCommand

from aldryn_forms.models import SubmittedToBeSent
from aldryn_forms.utils import send_postponed_notifications


class Command(BaseCommand):
    help = "Send postponed emails."

    def handle(self, *args, **options):
        for instance in SubmittedToBeSent.objects.all():
            if send_postponed_notifications(instance):
                instance.delete()
