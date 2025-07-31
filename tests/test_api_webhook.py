import json
from datetime import datetime, timezone

from django.test import SimpleTestCase, TestCase

import responses
from freezegun import freeze_time
from requests.exceptions import HTTPError
from testfixtures import LogCapture

from aldryn_forms.api.serializers import FormSubmissionSerializer
from aldryn_forms.api.webhook import (
    collect_submissions_data, process_match, send_submissions_data, send_to_webhook, transform_data, trigger_webhooks,
)
from aldryn_forms.models import FormSubmission, Webhook


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
                send_to_webhook(self.url, "JSON", data)
        self.log_handler.check()

    def test_response(self):
        data = {
            'hostname': 'testserver',
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
            response = send_to_webhook(self.url, "JSON", serializer.data)
        self.assertEqual(response.json(), response_data)
        self.assertJSONEqual(payload, data)
        self.log_handler.check()


@freeze_time(datetime(2025, 3, 13, 8, 10, tzinfo=timezone.utc))
class TriggerWebhookTest(Mixin, TestCase):

    def setUp(self):
        super().setUp()
        Webhook.objects.create(name="Test", url=self.url)

    def test_connection_failed(self):
        webhooks = Webhook.objects.all()
        data = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        submission = FormSubmission.objects.create(name="Test", data=data)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            trigger_webhooks(webhooks, submission, "testserver")
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'testserver', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-13T03:10:00-05:00', 'form_recipients': [], 'form_data': "
            "[{'name': 'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]}"),
            ('aldryn_forms.api.webhook', 'ERROR', 'https://host.foo/webhook/ Connection failed.')
        )

    def test(self):
        webhooks = Webhook.objects.all()
        data = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        submission = FormSubmission.objects.create(name="Test", data=data)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
            trigger_webhooks(webhooks, submission, "testserver")
        self.log_handler.check((
            'aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'testserver', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-13T03:10:00-05:00', 'form_recipients': [], 'form_data': "
            "[{'name': 'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]}"
        ))


class ProcessMatchTest(Mixin, SimpleTestCase):

    def test_pattern(self):
        self.assertEqual(process_match("t(.+s)t", "test"), "es")
        self.log_handler.check()

    def test_invalid_pattern(self):
        self.assertEqual(process_match("t(.+st", "test"), "test")
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', 't(.+st missing ), unterminated subpattern at position 1'),
        )

    def test_pattern_without_group(self):
        self.assertEqual(process_match("t.+st", "test"), "")
        self.log_handler.check()

    def test_flags(self):
        self.assertEqual(process_match(["t(.+s)t", "AIS"], "TEST"), "ES")
        self.log_handler.check()

    def test_unknown_flags(self):
        self.assertEqual(process_match(["t(.+s)t", "BO"], "TEST"), "TEST")
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', "B module 're' has no attribute 'B'"),
        )

    def test_default_separator(self):
        self.assertEqual(process_match("t(.+)s(.+)", "test"), "e t")
        self.log_handler.check()

    def test_custom_separator(self):
        self.assertEqual(process_match(["t(.+)s(.+)", "", "-"], "test"), "e-t")
        self.log_handler.check()

    def test_pattern_as_array(self):
        self.assertEqual(process_match(["t(.+)s(.+)"], "test"), "e t")
        self.log_handler.check()


class TransformDataTest(Mixin, SimpleTestCase):

    def test_no_rules(self):
        self.assertEqual(transform_data(None, {}), {})
        self.log_handler.check()

    def test_value(self):
        rules = [
            {"dest": "answer", "value": "42"},
        ]
        self.assertEqual(transform_data(rules, {}), {
            "answer": "42"
        })
        self.log_handler.check()

    def test_invalid_fnc(self):
        rules = [
            {"dest": "answer", "fnc": "foo"},
        ]
        self.assertEqual(transform_data(rules, {}), {})
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', "foo foo doesn't look like a module path"),
        )

    def test_unkonwn_fnc(self):
        rules = [
            {"dest": "answer", "fnc": "foo.name"},
        ]
        self.assertEqual(transform_data(rules, {}), {})
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', "foo.name No module named 'foo'"),
        )

    def test_fnc_without_params(self):
        rules = [
            {"dest": "answer", "fnc": "aldryn_forms.api.utils.remove_identical_value"},
        ]
        self.assertEqual(transform_data(rules, {}), {})
        self.log_handler.check()

    def test_fnc_with_params(self):
        data = {
            "one": "42",
            "two": "42",
        }
        rules = [
            {"dest": "answer", "value": "42"},
            {"dest": "question", "value": "42"},
            {
                "dest": "question",
                "fnc": "aldryn_forms.api.utils.remove_identical_value",
                "params": {
                    "fields": ["one", "two"]
                }
            },
        ]
        self.assertEqual(transform_data(rules, data), {"answer": "42"})
        self.log_handler.check()

    def test_jq(self):
        data = {"question": "42"}
        rules = [
            {"dest": "answer", "src": ".question"},
        ]
        self.assertEqual(transform_data(rules, data), {
            "answer": "42"
        })
        self.log_handler.check()

    def test_invalid_jq(self):
        data = {"question": "42"}
        rules = [
            {"dest": "answer", "src": ".question[.foo"},
        ]
        self.assertEqual(transform_data(rules, data), {})
        self.assertEqual(
            self.log_handler.records[0].msg[:62], ".question[.foo jq: error: syntax error, unexpected end of file")

    def test_stop_iteration(self):
        data = {"question": "42"}
        rules = [
            {"dest": "answer", "src": ".question[42]"},
        ]
        self.assertEqual(transform_data(rules, data), {})
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'DEBUG', 'StopIteration .question[42] Cannot index string with number'),
        )

    def test_jq_default_fetcher(self):
        data = {"questions": [1, 2, 3]}
        rules = [
            {"dest": "answer", "src": ".questions[]"},
        ]
        self.assertEqual(transform_data(rules, data), {
            "answer": "1"
        })
        self.log_handler.check()

    def test_jq_fetcher_all(self):
        data = {"questions": [1, 2, 3]}
        rules = [
            {"dest": "answer", "src": ".questions[]", "fetcher": "all"},
        ]
        self.assertEqual(transform_data(rules, data), {
            "answer": "[1, 2, 3]"
        })
        self.log_handler.check()

    def test_jq_default_separator(self):
        data = {"q": [1, 2, 3]}
        rules = [
            {"dest": "answer", "src": [".q[0]", ".q[1]", ".q[2]"]},
        ]
        self.assertEqual(transform_data(rules, data), {
            "answer": "1 2 3"
        })
        self.log_handler.check()

    def test_jq_custom_separator(self):
        data = {"q": [1, 2, 3]}
        rules = [
            {"dest": "answer", "src": [".q[0]", ".q[1]", ".q[2]"], "sep": "+"},
        ]
        self.assertEqual(transform_data(rules, data), {
            "answer": "1+2+3"
        })
        self.log_handler.check()

    def test_jq_and_match(self):
        data = {"question": "The answer is 42."}
        rules = [
            {"dest": "answer", "src": ".question", "match": r".+?(\d+)"},
        ]
        self.assertEqual(transform_data(rules, data), {
            "answer": "42"
        })
        self.log_handler.check()

    def test_jq_and_match_no_value(self):
        data = {"question": "The answer is 42."}
        rules = [
            {"dest": "answer", "src": ".question", "match": ".+(X*)"},
        ]
        self.assertEqual(transform_data(rules, data), {})
        self.log_handler.check()


@freeze_time(datetime(2025, 3, 25, 9, 35, tzinfo=timezone.utc))
class CollectSubmissionsDataTest(Mixin, TestCase):

    def test(self):
        post = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        FormSubmission.objects.create(name="Test", data=post)
        hook = Webhook.objects.create(name="Test", url=self.url)
        data = collect_submissions_data(hook, FormSubmission.objects.all(), "localhost")
        self.assertEqual(data, [{
            'hostname': 'localhost',
            'name': 'Test',
            'language': 'en',
            'sent_at': '2025-03-25T04:35:00-05:00',
            'form_recipients': [],
            'form_data': [{'name': 'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]
        }])
        self.log_handler.check()


@freeze_time(datetime(2025, 3, 25, 9, 35, tzinfo=timezone.utc))
class SendSubmissionDataTest(Mixin, TestCase):

    def test_connection_failed(self):
        post = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        FormSubmission.objects.create(name="Test", data=post)
        hook = Webhook.objects.create(name="Test", url=self.url)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            send_submissions_data(hook, FormSubmission.objects.all(), "localhost")
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'localhost', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-25T04:35:00-05:00', 'form_recipients': [], 'form_data': [{'name': "
            "'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]}"),
            ('aldryn_forms.api.webhook', 'ERROR', 'https://host.foo/webhook/ Connection failed.'),
        )

    def test_send(self):
        post = json.dumps([
            {"label": "Test", "name": "test", "value": 1},
        ])
        FormSubmission.objects.create(name="Test", data=post)
        hook = Webhook.objects.create(name="Test", url=self.url)
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps({"status": "SUCCESS"}))
            send_submissions_data(hook, FormSubmission.objects.all(), "localhost")
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'DEBUG',
            "{'hostname': 'localhost', 'name': 'Test', 'language': 'en', 'sent_at': "
            "'2025-03-25T04:35:00-05:00', 'form_recipients': [], 'form_data': [{'name': "
            "'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]}"),
        )
