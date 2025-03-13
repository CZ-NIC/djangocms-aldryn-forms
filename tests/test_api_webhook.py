import json
from datetime import datetime, timezone

from django.test import TestCase

import responses
from freezegun import freeze_time
from requests.exceptions import HTTPError
from testfixtures import LogCapture

from aldryn_forms.api.serializers import FormSubmissionSerializer
from aldryn_forms.api.webhook import send_to_webook, trigger_webhooks
from aldryn_forms.models import FormSubmission, Webook


class Mixin:

    def setUp(self):
        self.url = "https://host.foo/webhook/"
        self.log_handler = LogCapture()
        self.addCleanup(self.log_handler.uninstall)


@freeze_time(datetime(2025, 3, 13, 8, 10, tzinfo=timezone.utc))
class SendToWebhookTest(Mixin, TestCase):

    def test_connection_failed(self):
        data = json.dumps([{"status": "OK"}])
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            with self.assertRaisesMessage(HTTPError, "Connection failed."):
                send_to_webook(self.url, data)
        self.log_handler.check()

    def test_response(self):
        data = {
            'name': 'Test',
            'language': 'en',
            'sent_at': '2025-03-13T03:10:00-05:00',
            'form_recipients': [],
            'form_data': [{'name': 'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]
        }
        post = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        submission = FormSubmission.objects.create(name="Test", data=post)
        serializer = FormSubmissionSerializer(submission)
        payload = json.dumps(serializer.data)
        response_data = {"status": "OK"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps(response_data))
            response = send_to_webook(self.url, payload)
        self.assertEqual(response.json(), response_data)
        self.assertJSONEqual(payload, data)
        self.log_handler.check()


class TriggerWebhookTest(Mixin, TestCase):

    def setUp(self):
        super().setUp()
        Webook.objects.create(name="Test", url=self.url)

    def test_connection_failed(self):
        webhooks = Webook.objects.all()
        data = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        submission = FormSubmission.objects.create(name="Test", data=data)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            trigger_webhooks(webhooks, submission)
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', 'https://host.foo/webhook/ Connection failed.')
        )

    def test(self):
        webhooks = Webook.objects.all()
        data = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        submission = FormSubmission.objects.create(name="Test", data=data)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
            trigger_webhooks(webhooks, submission)
        self.log_handler.check()
