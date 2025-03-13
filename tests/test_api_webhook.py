import json

from django.test import SimpleTestCase, TestCase

import responses
from requests.exceptions import HTTPError
from testfixtures import LogCapture

from aldryn_forms.api.webhook import send_to_webook, trigger_webhooks
from aldryn_forms.models import FormSubmission, Webook


class Mixin:

    def setUp(self):
        self.url = "https://host.foo/webhook/"
        self.log_handler = LogCapture()
        self.addCleanup(self.log_handler.uninstall)


class SendToWebhookTest(Mixin, SimpleTestCase):

    def test_connection_failed(self):
        data = json.dumps([{"status": "OK"}])
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            with self.assertRaisesMessage(HTTPError, "Connection failed."):
                send_to_webook(self.url, data)
        self.log_handler.check()

    def test_response(self):
        data = [{"status": "OK"}]
        body = json.dumps(data)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=body)
            response = send_to_webook(self.url, body)
        self.assertEqual(response.json(), data)
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
            ('aldryn_forms.api.webhook', 'ERROR', 'Connection failed.')
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
