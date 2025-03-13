from django.contrib.auth.models import User
from django.core import mail

from cms.api import add_plugin, create_page
from cms.test_utils.testcases import CMSTestCase

import responses

from aldryn_forms.models import FormPlugin, FormSubmission
from tests.test_views import CMS_3_6


class FormPluginTestCase(CMSTestCase):

    def setUp(self):
        super().setUp()

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
        self.form_plugin = add_plugin(self.placeholder, 'FormPlugin', 'en', **plugin_data)
        self.form_plugin.recipients.add(self.user)

        add_plugin(self.placeholder, 'TextField', 'en', target=self.form_plugin, label="Name", name="name")
        add_plugin(self.placeholder, 'SubmitButton', 'en', target=self.form_plugin)

    def _check_mailbox(self):
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "email@example.com")
        self.assertEqual(msg.get("subject"), "[Form submission] Contact us")
        part_text, part_html = msg.get_payload()
        self.assertEqual(part_text.get_payload(), '\nForm name: Contact us\nName: Tester\n\n\n')
        self.assertInHTML(
            "<html><head></head><body><p>Form name: Contact us</p><p>Name: Tester</p></body></html>",
            part_html.get_payload())

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


class EmailNotificationFormPluginTestCase(CMSTestCase):
    def setUp(self):
        super().setUp()

        self.page = create_page('test page', 'test_page.html', 'en', published=True)
        try:
            self.placeholder = self.page.placeholders.get(slot='content')
        except AttributeError:
            self.placeholder = self.page.get_placeholders('en').get(slot='content')
        self.user = User.objects.create_superuser('username', 'email@example.com', 'password')

        plugin_data = {
            'redirect_type': 'redirect_to_url',
            'url': 'http://www.google.com',
        }
        self.form_plugin = add_plugin(self.placeholder, 'EmailNotificationForm', 'en', **plugin_data)
        self.form_plugin.email_notifications.create(to_user=self.user, theme='default')

        add_plugin(self.placeholder, 'SubmitButton', 'en', target=self.form_plugin)

    def test_form_submission_default_action(self):
        self.form_plugin.action_backend = 'default'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        response = self.client.post(self.page.get_absolute_url('en'), {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_form_submission_email_action(self):
        self.form_plugin.action_backend = 'email_only'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        response = self.client.post(self.page.get_absolute_url('en'), {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_form_submission_no_action(self):
        self.form_plugin.action_backend = 'none'
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish('en')

        response = self.client.post(self.page.get_absolute_url('en'), {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
