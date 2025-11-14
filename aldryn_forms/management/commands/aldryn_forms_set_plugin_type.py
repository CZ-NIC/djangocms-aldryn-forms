import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from aldryn_forms.models import FormSubmission


class Command(BaseCommand):
    help = "Set attribute plugin_type into submitted data defined by name."

    def add_arguments(self, parser):
        parser.add_argument("keys", nargs="+", type=str)
        parser.add_argument(
            "--datetime-from",
            help="Select only submissions from the datetime.",
        )
        parser.add_argument(
            "--datetime-to",
            help="Select only submissions to the datetime.",
        )

    def handle(self, *args, **options):
        translations = {}
        for key in options["keys"]:
            data = key.split(":")
            if len(data) != 2:
                raise CommandError('Invalid key "%s". It must be in format "field_name:plugin_type".' % key)
            translations[data[0]] = data[1]
        queryset = FormSubmission.objects.all()
        if options["datetime_from"]:
            datetime_from = parse_datetime(options["datetime_from"])
            if options["datetime_to"]:
                datetime_to = parse_datetime(options["datetime_to"])
                queryset = queryset.filter(sent_at__range=(datetime_from, datetime_to))
            else:
                queryset = queryset.filter(sent_at=datetime_from)
        updated = 0
        for submission in queryset:
            data = submission.get_form_data()
            modified_data = []
            modified = False
            for item in data:
                sfield = item._asdict()
                if item.name in translations:
                    sfield["plugin_type"] = translations[item.name]
                    modified = True
                modified_data.append(sfield)
            if modified:
                submission.data = json.dumps(modified_data)
                submission.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS('Updated submissions: %s' % updated))
