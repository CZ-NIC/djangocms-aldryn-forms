import json
from datetime import datetime, timezone

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings

import responses
from freezegun import freeze_time
from testfixtures import LogCapture

from aldryn_forms.models import FormSubmission, SubmittedToBeSent, Webook


@override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
class RemoveExpiredPostIdentsTest(TestCase):

    data = [
        {"label": "Test", "name": "test", "value": 1},
    ]

    def test_not_yet_removed(self):
        with freeze_time(datetime(2025, 3, 14, 9, 0, tzinfo=timezone.utc)):
            FormSubmission.objects.create(name="Test", data=json.dumps(self.data), post_ident="1234567890")
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            call_command("aldryn_forms_remove_expired_post_idents")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('post_ident'), [("1234567890",)], transform=None)

    def test_post_ident_removed(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            FormSubmission.objects.create(name="Test", data=json.dumps(self.data), post_ident="1234567890")
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            call_command("aldryn_forms_remove_expired_post_idents")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('post_ident'), [(None,)], transform=None)


@override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
class SendEmailsTest(TestCase):

    data = [
        {"label": "Test", "name": "test", "value": 1},
    ]
    recipients = [
        {"name": "Dave", "email": "dave@foo.foo"}
    ]

    def setUp(self):
        self.url = "https://host.foo/webhook/"
        self.log_handler = LogCapture()
        self.addCleanup(self.log_handler.uninstall)

    def test_not_yet_removed(self):
        with freeze_time(datetime(2025, 3, 14, 9, 0, tzinfo=timezone.utc)):
            tosent = SubmittedToBeSent.objects.create(
                name="Test",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890"
            )
        webhook = Webook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock():
                call_command("aldryn_forms_send_emails")
        self.assertQuerySetEqual(SubmittedToBeSent.objects.values_list('post_ident'), [("1234567890",)], transform=None)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check()

    def test_post_removed(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            tosent = SubmittedToBeSent.objects.create(
                name="Test",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890"
            )
        webhook = Webook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock() as rsps:
                rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
                call_command("aldryn_forms_send_emails")
        self.assertEqual(SubmittedToBeSent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")
        self.assertEqual(msg.get("subject"), "[Form submission] Test")
        self.log_handler.check()
