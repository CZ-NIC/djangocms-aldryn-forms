import json
import os
import shutil
import tempfile
from typing import Any
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from cms.test_utils.testcases import CMSTestCase

from testfixtures import LogCapture

from aldryn_forms.action_backends import DefaultAction, EmailAction, NoAction
from aldryn_forms.action_backends_base import BaseAction
from aldryn_forms.models import FormSubmission, SerializedFormField
from aldryn_forms.utils import (
    action_backend_choices, get_action_backends, get_upload_urls, prepare_attachments, send_postponed_notifications,
)


_SETTINGS: dict[str, Any] = {}


def setUpModule():
    _SETTINGS["folder"] = tempfile.mkdtemp()
    os.makedirs(os.path.join(_SETTINGS["folder"], "filer_public"))
    os.makedirs(os.path.join(_SETTINGS["folder"], "filer_private"))
    with open(os.path.join(_SETTINGS["folder"], "filer_public/hello.txt"), "w") as handle:
        handle.write("Hello world!")
    with open(os.path.join(_SETTINGS["folder"], "filer_private/hello.txt"), "w") as handle:
        handle.write("Hello private world!")


def tearDownModule():
    shutil.rmtree(_SETTINGS["folder"])


class FakeValidBackend(BaseAction):
    verbose_name = 'Fake Valid Backend'

    def form_valid(self, cmsplugin, instance, request, form):
        pass


class FakeValidBackend2(BaseAction):
    verbose_name = 'Another Fake Valid Backend'

    def form_valid(self, cmsplugin, instance, request, form):
        pass


class FakeInvalidBackendNoInheritance():
    verbose_name = 'Fake Invalid Backend (no inheritance)'

    def form_valid(self, cmsplugin, instance, request, form):
        pass


class FakeInvalidBackendNoVerboseName(BaseAction):
    def form_valid(self, cmsplugin, instance, request, form):
        pass


class FakeInvalidBackendNoFormValid(BaseAction):
    verbose_name = 'Fake Invalid Backend (no form_valid() definition)'


class GetActionsTestCase(CMSTestCase):
    def test_default_backends(self):
        expected = {
            'default': DefaultAction,
            'email_only': EmailAction,
            'none': NoAction,
        }

        backends = get_action_backends()

        self.assertDictEqual(backends, expected)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.test_utils.FakeValidBackend',
        'x': 'tests.test_utils.FakeValidBackend2',
    })
    def test_override_valid(self):
        expected = {
            'default': FakeValidBackend,
            'x': FakeValidBackend2,
        }

        backends = get_action_backends()

        self.assertDictEqual(backends, expected)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.test_utils.FakeValidBackend',
        'x' * 100: 'tests.test_utils.FakeValidBackend2',
    })
    def test_override_invalid_keys_too_big(self):
        self.assertRaises(ImproperlyConfigured, get_action_backends)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.whatever.something.terribly.Wrong',
    })
    def test_override_invalid_path_to_class_not_found(self):
        self.assertRaises(ImproperlyConfigured, get_action_backends)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.test_utils.FakeInvalidBackendNoInheritance',
    })
    def test_override_invalid_class_does_not_inherit_from_base_action_backend(self):
        self.assertRaises(ImproperlyConfigured, get_action_backends)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'custom': 'tests.test_utils.FakeValidBackend',
    })
    def test_override_invalid_key_default_missing(self):
        self.assertRaises(ImproperlyConfigured, get_action_backends)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.test_utils.FakeInvalidBackendNoVerboseName',
    })
    def test_override_invalid_class_does_not_define_verbose_name(self):
        self.assertRaises(ImproperlyConfigured, get_action_backends)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.test_utils.FakeInvalidBackendNoFormValid',
    })
    def test_override_invalid_class_does_not_define_form_valid(self):
        self.assertRaises(ImproperlyConfigured, get_action_backends)


class ActionChoicesTestCase(CMSTestCase):
    def test_default_backends(self):
        expected = [
            ('none', 'No action'),
            ('email_only', 'Only send email'),
            ('default', 'Save to site administration and send email'),
        ]

        choices = action_backend_choices()

        self.assertEqual(choices, expected)

    @override_settings(ALDRYN_FORMS_ACTION_BACKENDS={
        'default': 'tests.test_utils.FakeValidBackend',
        'x': 'tests.test_utils.FakeValidBackend2',
    })
    def test_override_valid(self):
        expected = [
            ('x', 'Another Fake Valid Backend'),
            ('default', 'Fake Valid Backend'),
        ]

        choices = action_backend_choices()

        self.assertEqual(choices, expected)


class SendPostponedNotificationsTest(CMSTestCase):

    data = [
        {"label": "Name", "name": "name", "value": "Tom Tester", "plugin_type": "TextField"},
        {"label": "E-mail", "name": "email", "value": "tester@example.com", "plugin_type": "EmailField"},
    ]
    recipients = [
        {"name": "Tom Tester", "email": "teser@example.com"},
    ]

    def test_subject(self):
        instance = FormSubmission.objects.create(
            name="Contact us", language="en", data=json.dumps(self.data), recipients=json.dumps(self.recipients))
        send_postponed_notifications(instance)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "teser@example.com")
        self.assertEqual(msg.get("subject"), "Contact us")

    @patch("aldryn_forms.utils.constance_config")
    def test_subject_from_constance(self, constance_config):
        constance_config.ALDRYN_FORMS_EMAIL_SUBJECT_EN = "Reply to ad {{ form_values.name }} ({{ form_values.email }})"
        instance = FormSubmission.objects.create(
            name="Contact us", language="en", data=json.dumps(self.data), recipients=json.dumps(self.recipients))
        send_postponed_notifications(instance)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "teser@example.com")
        self.assertEqual(msg.get("subject"), "Reply to ad Tom Tester (tester@example.com)")


class GetUploadUrlsTest(CMSTestCase):

    def test(self):
        form_data = [
            SerializedFormField("name", "Name", 1, "Tom", "TextField"),
            SerializedFormField("att1", "Att 1", 1, "file", "FileField"),
            SerializedFormField("att2", "Att 2", 1, "image", "ImageField"),
            SerializedFormField("att3", "Att 3", 1, "one/two", "MultipleFilesField"),
            SerializedFormField("att4", "Att 4", 1, "file", "FileField"),
        ]
        self.assertEqual(get_upload_urls(form_data), {'one/two', 'file', 'image'})


class PrepareAttachmentsTest(CMSTestCase):

    log_name = "aldryn_forms.utils"

    def test_file_missing(self):
        url = os.path.join(settings.MEDIA_URL, "filer_public/test.txt")
        with override_settings(MEDIA_ROOT=_SETTINGS["folder"]):
            with LogCapture(self.log_name) as log_handler:
                response = prepare_attachments([url])
        self.assertEqual(response, [])
        log_handler.check((
            'aldryn_forms.utils',
            'ERROR',
            '[Errno 2] No such file or directory: '
            f"'{_SETTINGS['folder']}/filer_public/test.txt'"
        ))

    def test_public(self):
        url = os.path.join(settings.MEDIA_URL, "filer_public/hello.txt")
        with override_settings(MEDIA_ROOT=_SETTINGS["folder"]):
            with LogCapture(self.log_name) as log_handler:
                response = prepare_attachments([url])
        self.assertEqual(response, [
            ("hello.txt", b"Hello world!"),
        ])
        log_handler.check()

    @override_settings(PRIVATE_MEDIA_URL_PREFIX="/smedia/")
    def test_private(self):
        url = os.path.join(settings.PRIVATE_MEDIA_URL_PREFIX, "filer_private/hello.txt")
        with override_settings(MEDIA_ROOT=_SETTINGS["folder"]):
            with LogCapture(self.log_name) as log_handler:
                response = prepare_attachments([url])
        self.assertEqual(response, [
            ("hello.txt", b"Hello private world!"),
        ])
        log_handler.check()
