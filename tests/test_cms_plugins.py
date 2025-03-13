import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings

from cms.api import add_plugin, create_page
from cms.test_utils.testcases import CMSTestCase

import responses
from requests.exceptions import HTTPError
from testfixtures import LogCapture

from aldryn_forms.models import FormPlugin, FormSubmission, SubmittedToBeSent, Webook
from tests.test_views import CMS_3_6


class DataMixin:

    plugin_name = ""

    def setUp(self):
        self.page = create_page('test page', 'test_page.html', 'en', published=True)
        try:
            self.placeholder = self.page.placeholders.get(slot='content')
        except AttributeError:
            self.placeholder = self.page.get_placeholders('en').get(slot='content')
        self.user = User.objects.create_superuser('username', 'email@example.com', 'password')

        plugin_data = {
            'redirect_type': 'redirect_to_url',
            'url': 'http://www.google.com',
            'name': 'Contact us',
        }
        self.form_plugin = add_plugin(self.placeholder, self.plugin_name, 'en', **plugin_data)
        add_plugin(self.placeholder, 'TextField', 'en', target=self.form_plugin, label="Name", name="name")
        add_plugin(self.placeholder, 'SubmitButton', 'en', target=self.form_plugin)
        # Webhook
        self.url = "https://host.foo/webhook/"
        self.webook = Webook.objects.create(name="Test", url=self.url)
        self.log_handler = LogCapture()
        self.addCleanup(self.log_handler.uninstall)

    def _check_mailbox(self):
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "email@example.com")
        self.assertEqual(msg.get("subject"), "[Form submission] Contact us")
        part_text, part_html = msg.get_payload()
        self.assertEqual(part_text.get_payload().strip(), 'Form name: Contact us\nName: Tester')
        self.assertInHTML(
            "<html><head></head><body><p>Form name: Contact us</p><p>Name: Tester</p></body></html>",
            part_html.get_payload())


class FormPluginTestCase(DataMixin, CMSTestCase):

    plugin_name = "FormPlugin"

    def setUp(self):
        super().setUp()
        self.form_plugin.recipients.add(self.user)

    def test_form_submission_default_action(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', None),
        ], transform=None)
        self._check_mailbox()
        self.log_handler.check()

    def test_form_submission_email_action(self):
        self.form_plugin.action_backend = 'email_only'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self._check_mailbox()
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO', 'Sent email notifications to 1 recipients.'),
        )

    def test_form_submission_no_action(self):
        self.form_plugin.action_backend = 'none'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO',
             f'Not persisting data for "{form_plugin.pk}" since action_backend is set to "none"'),
        )

    def test_form_submission_default_action_with_webhook_failure(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', None),
        ], transform=None)
        self._check_mailbox()
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', 'https://host.foo/webhook/ Connection failed.')
        )

    def test_form_submission_default_action_with_webhook(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', None),
        ], transform=None)
        self._check_mailbox()
        self.log_handler.check()

    def test_form_submission_email_action_webhook(self):
        self.form_plugin.action_backend = 'email_only'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self._check_mailbox()
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO', 'Sent email notifications to 1 recipients.'),
        )

    def test_form_submission_no_action_webhook(self):
        self.form_plugin.action_backend = 'none'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO',
             f'Not persisting data for "{form_plugin.pk}" since action_backend is set to "none"'),
        )

    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    @patch("aldryn_forms.forms.get_random_string", lambda size: "BJKHAmxW")
    def test_postponed_form_submission_default_action_with_webhook(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', "BJKHAmxW"),
        ], transform=None)
        self.assertQuerySetEqual(SubmittedToBeSent.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', "BJKHAmxW"),
        ], transform=None)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check()


class EmailNotificationFormPluginTestCase(DataMixin, CMSTestCase):

    plugin_name = "EmailNotificationForm"

    def setUp(self):
        super().setUp()
        self.form_plugin.email_notifications.create(to_user=self.user, theme='default')

    def test_form_submission_default_action(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', None),
        ], transform=None)
        self._check_mailbox()
        self.log_handler.check()

    def test_form_submission_email_action(self):
        self.form_plugin.action_backend = 'email_only'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self._check_mailbox()
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO', 'Sent email notifications to 1 recipients.'),
        )

    def test_form_submission_no_action(self):
        self.form_plugin.action_backend = 'none'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO',
             f'Not persisting data for "{form_plugin.pk}" since action_backend is set to "none"'),
        )

    def test_form_submission_default_action_webhook_failure(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=HTTPError("Connection failed."))
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', None),
        ], transform=None)
        self._check_mailbox()
        self.log_handler.check(
            ('aldryn_forms.api.webhook', 'ERROR', 'https://host.foo/webhook/ Connection failed.')
        )

    def test_form_submission_default_action_webhook(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock() as rsps:
            rsps.add(responses.POST, self.url, body=json.dumps([{"status": "OK"}]))
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list(
            "name", "data", "post_ident").all().order_by('pk'), [
            ('Contact us', '[{"name": "name", "label": "Name", "field_occurrence": 1, "value": "Tester"}]', None),
        ], transform=None)
        self._check_mailbox()
        self.log_handler.check()

    def test_form_submission_no_action_webhook(self):
        self.form_plugin.action_backend = 'none'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        form_plugin = FormPlugin.objects.last()
        form_plugin.webhooks.add(self.webook)
        data = {"language": "en", "form_plugin_id": form_plugin.pk, "name": "Tester"}
        with responses.RequestsMock():
            response = self.client.post(self.page.get_absolute_url('en'), data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.log_handler.check(
            ('aldryn_forms.action_backends', 'INFO',
             f'Not persisting data for "{form_plugin.pk}" since action_backend is set to "none"'),
        )
