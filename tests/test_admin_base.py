import json
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

import responses
from freezegun import freeze_time
from testfixtures import LogCapture

from aldryn_forms.models import FormSubmission, Webhook


@freeze_time(datetime(2025, 3, 25, 12, 45, tzinfo=timezone.utc))
class AdminActionsTest(TestCase):

    def setUp(self):
        self.url = "http://example.com/"
        self.hook = Webhook.objects.create(name="Test", url=self.url, method="post")
        self.sub1 = FormSubmission.objects.create(name="Test 1", data=json.dumps([
            {"label": "Test 1", "name": "test", "value": 1}]))
        self.sub2 = FormSubmission.objects.create(name="Test 2", data=json.dumps([
            {"label": "Test 2", "name": "test", "value": 2}]))

        self.log_handler = LogCapture()
        self.addCleanup(self.log_handler.uninstall)

        user = get_user_model().objects.create(username="admin", is_active=True, is_staff=True, is_superuser=True)
        self.client.force_login(user)

    def test_webhook_export_without_parameter(self):
        response = self.client.get(reverse("admin:webhook_export"))
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.assertEqual([str(msg) for msg in get_messages(response.wsgi_request)], [
            "Items must be selected in order to perform actions on them. No items have been changed."
        ])
        self.log_handler.check()

    def test_webhook_export_get(self):
        response = self.client.get(reverse("admin:webhook_export") + "?ids=42")
        self.assertContains(response, f"""
            <select name="webhook" id="id_webhook">
                <option value="{self.hook.pk}">Test</option>
            </select>""", html=True)
        self.log_handler.check()

    def test_webhook_export_missing_items(self):
        response = self.client.post(reverse("admin:webhook_export") + "?ids=42")
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.assertEqual([str(msg) for msg in get_messages(response.wsgi_request)], [
            "Missing items for processing."
        ])
        self.log_handler.check()

    def test_webhook_export_invalid_post(self):
        response = self.client.post(reverse("admin:webhook_export") +
                                    f"?ids={self.sub1.pk}.{self.sub2.pk}", {"webhook": "42"})
        self.assertEqual([str(msg) for msg in get_messages(response.wsgi_request)], [
            '* webhook\n  * Select a valid choice. 42 is not one of the available choices.'
        ])
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.log_handler.check()

    def test_webhook_export_post(self):
        response = self.client.post(reverse("admin:webhook_export") +
                                    f"?ids={self.sub1.pk}.{self.sub2.pk}", {"webhook": self.hook.pk})
        self.assertEqual(response["Content-type"], "application/json")
        self.assertEqual(response.json(), {
            'data': [
                {'hostname': 'example.com', 'name': 'Test 1', 'language': 'en',
                 'sent_at': '2025-03-25T07:45:00-05:00', 'form_recipients': [],
                 'form_data': [{'name': 'test', 'label': 'Test 1', 'field_occurrence': 1, 'value': 1}]
                 },
                {'hostname': 'example.com', 'name': 'Test 2', 'language': 'en',
                 'sent_at': '2025-03-25T07:45:00-05:00', 'form_recipients': [],
                 'form_data': [{'name': 'test', 'label': 'Test 2', 'field_occurrence': 1, 'value': 2}]
                 }
            ]})
        self.log_handler.check()

    def test_send_webhook_without_parameter(self):
        response = self.client.get(reverse("admin:webhook_send"))
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.assertEqual([str(msg) for msg in get_messages(response.wsgi_request)], [
            "Items must be selected in order to perform actions on them. No items have been changed."
        ])
        self.log_handler.check()

    def test_send_webhook_get(self):
        response = self.client.get(reverse("admin:webhook_send") + "?ids=42")
        self.assertContains(response, f"""
            <select name="webhook" id="id_webhook">
                <option value="{self.hook.pk}">Test</option>
            </select>""", html=True)
        self.log_handler.check()

    def test_send_webhook_missing_items(self):
        response = self.client.post(reverse("admin:webhook_send") + "?ids=42")
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.assertEqual([str(msg) for msg in get_messages(response.wsgi_request)], [
            "Missing items for processing."
        ])
        self.log_handler.check()

    def test_send_webhook_post(self):
        response_data = {"status": "OK"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps(response_data))
            rsps.add(responses.POST, self.url, body=json.dumps(response_data))
            response = self.client.post(reverse("admin:webhook_send") +
                                        f"?ids={self.sub1.pk}.{self.sub2.pk}", {"webhook": self.hook.pk})
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'DEBUG',
             "{'hostname': 'example.com', 'name': 'Test 1', 'language': 'en', 'sent_at': "
             "'2025-03-25T07:45:00-05:00', 'form_recipients': [], 'form_data': [{'name': "
             "'test', 'label': 'Test 1', 'field_occurrence': 1, 'value': 1}]}"),
            ('aldryn_forms.api.webhook', 'DEBUG',
             "{'hostname': 'example.com', 'name': 'Test 2', 'language': 'en', 'sent_at': "
             "'2025-03-25T07:45:00-05:00', 'form_recipients': [], 'form_data': [{'name': "
             "'test', 'label': 'Test 2', 'field_occurrence': 1, 'value': 2}]}"),
        )

    def test_action_export_webhook(self):
        data = {"action": "export_webhook", "_selected_action": [str(self.sub1.pk), str(self.sub2.pk)]}
        response = self.client.post(reverse("admin:aldryn_forms_formsubmission_changelist"), data)
        self.assertRedirects(
            response, reverse("admin:webhook_export") + f"?ids={self.sub2.pk}.{self.sub1.pk}",
            fetch_redirect_response=False)
        self.log_handler.check()

    def test_action_send_webhook(self):
        data = {"action": "send_webhook", "_selected_action": [str(self.sub1.pk), str(self.sub2.pk)]}
        response = self.client.post(reverse("admin:aldryn_forms_formsubmission_changelist"), data)
        self.assertRedirects(
            response, reverse("admin:webhook_send") + f"?ids={self.sub2.pk}.{self.sub1.pk}",
            fetch_redirect_response=False)
        self.log_handler.check()

    def test_action_honeypot_filled_on(self):
        data = {"action": "honeypot_filled_on", "_selected_action": [str(self.sub1.pk)]}
        response = self.client.post(reverse("admin:aldryn_forms_formsubmission_changelist"), data)
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.assertQuerySetEqual(FormSubmission.objects.values_list("name", "honeypot_filled").order_by("name"), [
            ("Test 1", True),
            ("Test 2", False),
        ], transform=None)
        self.log_handler.check()

    def test_action_honeypot_filled_off(self):
        sub3 = FormSubmission.objects.create(name="Test 3", data=json.dumps([
            {"label": "Test 3", "name": "test", "value": 3}]), honeypot_filled=True)
        data = {"action": "honeypot_filled_off", "_selected_action": [str(sub3.pk)]}
        response = self.client.post(reverse("admin:aldryn_forms_formsubmission_changelist"), data)
        self.assertRedirects(
            response, reverse("admin:aldryn_forms_formsubmission_changelist"), fetch_redirect_response=False)
        self.assertQuerySetEqual(FormSubmission.objects.values_list("name", "honeypot_filled").order_by("name"), [
            ("Test 1", False),
            ("Test 2", False),
            ("Test 3", False),
        ], transform=None)
        self.log_handler.check()

    @override_settings(ALDRYN_FORMS_SUBMISSION_LIST_DISPLAY_FIELD="aldryn_forms.admin.display_form_submission_data")
    def test_formsubmission_changelist(self):
        response = self.client.get(reverse("admin:aldryn_forms_formsubmission_changelist"))
        self.assertContains(response, """
            <td class="field-display_data">
                <span class="aldryn-forms-data">
                    <span class="item">
                        <span class="label">Test 1</span>
                        <span class="value">1</span>
                    </span>
                </span>
            </td>""", html=True)
        self.assertContains(response, """
            <td class="field-display_data">
                <span class="aldryn-forms-data">
                    <span class="item">
                        <span class="label">Test 2</span>
                        <span class="value">2</span>
                    </span>
                </span>
            </td>""", html=True)
