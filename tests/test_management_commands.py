from io import StringIO
import json
import smtplib
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings

import responses
from freezegun import freeze_time
from testfixtures import LogCapture

from aldryn_forms.models import FormSubmission, SubmittedToBeSent, Webhook


@override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
class RemoveExpiredPostIdentsTest(TestCase):

    data = [
        {"label": "Test", "name": "test", "value": 1},
    ]

    def test_not_yet_removed(self):
        with freeze_time(datetime(2025, 3, 14, 9, 0, tzinfo=timezone.utc)):
            FormSubmission.objects.create(name="Test", language="en", data=json.dumps(self.data), post_ident="1234567890")
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            call_command("aldryn_forms_remove_expired_post_idents")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('post_ident'), [("1234567890",)], transform=None)

    def test_post_ident_removed(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            FormSubmission.objects.create(name="Test", language="en", data=json.dumps(self.data), post_ident="1234567890")
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            call_command("aldryn_forms_remove_expired_post_idents")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('post_ident'), [(None,)], transform=None)

    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=0)
    def test_disabled(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            FormSubmission.objects.create(name="Test", language="en", data=json.dumps(self.data), post_ident="1234567890")
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            call_command("aldryn_forms_remove_expired_post_idents")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('post_ident'), [("1234567890",)], transform=None)


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
                language="en",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890"
            )
        webhook = Webhook.objects.create(name="Test", url=self.url)
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
                language="en",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890"
            )
        webhook = Webhook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock() as rsps:
                rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
                call_command("aldryn_forms_send_emails")
        self.assertEqual(SubmittedToBeSent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")
        self.assertEqual(msg.get("subject"), "Test")
        self.log_handler.check((
            'aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'example.com', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-14T03:59:59-05:00', 'form_recipients': [{'name': 'Dave', 'email': "
            "'dave@foo.foo'}], 'form_data': [{'name': 'test', 'label': 'Test', "
            "'field_occurrence': 1, 'value': 1, 'plugin_type': ''}]}"
        ))

    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=0)
    def test_disabled(self):
        with freeze_time(datetime(2025, 3, 14, 9, 0, tzinfo=timezone.utc)):
            tosent = SubmittedToBeSent.objects.create(
                name="Test",
                language="en",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890"
            )
        webhook = Webhook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock() as rsps:
                rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
                call_command("aldryn_forms_send_emails")
        self.assertEqual(SubmittedToBeSent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")
        self.assertEqual(msg.get("subject"), "Test")
        self.log_handler.check((
            'aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'example.com', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-14T04:00:00-05:00', 'form_recipients': [{'name': 'Dave', 'email': "
            "'dave@foo.foo'}], 'form_data': [{'name': 'test', 'label': 'Test', "
            "'field_occurrence': 1, 'value': 1, 'plugin_type': ''}]}"
        ))

    def test_honeypot_filled(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            tosent = SubmittedToBeSent.objects.create(
                name="Test",
                language="en",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890",
                honeypot_filled=True
            )
        webhook = Webhook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock():
                call_command("aldryn_forms_send_emails")
        self.assertEqual(SubmittedToBeSent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check()

    @patch("aldryn_forms.utils.send_mail", Mock(side_effect=smtplib.SMTPException("STOP!")))
    def test_send_mail_failed(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            tosent = SubmittedToBeSent.objects.create(
                name="Test",
                language="en",
                data=json.dumps(self.data),
                recipients=json.dumps(self.recipients),
                post_ident="1234567890"
            )
        webhook = Webhook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock():
                call_command("aldryn_forms_send_emails")
        self.assertEqual(SubmittedToBeSent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check(('aldryn_forms.utils', 'ERROR', 'STOP!'),)

    def test_no_recipients(self):
        with freeze_time(datetime(2025, 3, 14, 8, 59, 59, tzinfo=timezone.utc)):
            tosent = SubmittedToBeSent.objects.create(
                name="Test",
                language="en",
                data=json.dumps(self.data),
                post_ident="1234567890"
            )
        webhook = Webhook.objects.create(name="Test", url=self.url)
        tosent.webhooks.add(webhook)
        with freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc)):
            with responses.RequestsMock() as rsps:
                rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
                call_command("aldryn_forms_send_emails")
        self.assertEqual(SubmittedToBeSent.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check((
            'aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'example.com', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-14T03:59:59-05:00', 'form_recipients': [], 'form_data': "
            "[{'name': 'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1, 'plugin_type': ''}]}"
        ))


class SetPluginTypeTest(TestCase):

    def test(self):
        FormSubmission.objects.create(name="Test", language="en", data=json.dumps([
            {"label": "Test", "name": "test", "value": 1},
            {"label": "Attach.", "name": "attachment", "value": 1},
        ]))
        output = StringIO()
        call_command("aldryn_forms_set_plugin_type", "attachment:FileField", stdout=output)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertJSONEqual(FormSubmission.objects.first().data, [
                {"label": "Test", "name": "test", "value": 1},
                {"label": "Attach.", "name": "attachment", "value": 1, "plugin_type": "FileField"},
        ])
        self.assertEqual(output.getvalue(), "\x1b[32;1mUpdated submissions: 1\x1b[0m\n")
