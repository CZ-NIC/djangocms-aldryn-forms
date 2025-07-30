import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from cms.api import add_plugin
from cms.models import Placeholder

from filer.models import Folder

from aldryn_forms.models import (
    FileUploadFieldPlugin, FormSubmission, ImageUploadFieldPlugin, MultipleFilesUploadFieldPlugin, Option, URLFieldPlugin
)


class OptionTestCase(TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.placeholder = Placeholder.objects.create(slot='test')
        self.field = add_plugin(self.placeholder, 'SelectField', 'en')

    def test_position_organic_ordering(self):
        ''' Tests that no manual ordering leads to an organic ordering: first added, first displayed. '''
        self.field.option_set.create(value='one')
        self.field.option_set.create(value='two')
        self.field.option_set.create(value='three')
        self.field.option_set.create(value='four')
        self.field.option_set.create(value='five')

        option1, option2, option3, option4, option5 = self.field.option_set.all()

        self.assertEqual(option1.value, 'one')
        self.assertEqual(option1.position, 10)
        self.assertEqual(option2.value, 'two')
        self.assertEqual(option2.position, 20)
        self.assertEqual(option3.value, 'three')
        self.assertEqual(option3.position, 30)
        self.assertEqual(option4.value, 'four')
        self.assertEqual(option4.position, 40)
        self.assertEqual(option5.value, 'five')
        self.assertEqual(option5.position, 50)

    def test_position_manual_ordering(self):
        self.field.option_set.create(position=100, value='below $10')
        self.field.option_set.create(position=200, value='between $10 and $50')
        self.field.option_set.create(position=10, value='super promo: below $1!')
        self.field.option_set.create(position=300, value='$50+ because you are rich')
        self.field.option_set.create(position=1, value='items for free (but they are broken - sorry)')

        option1, option2, option3, option4, option5 = self.field.option_set.all()

        self.assertEqual(option1.value, 'items for free (but they are broken - sorry)')
        self.assertEqual(option1.position, 1)
        self.assertEqual(option2.value, 'super promo: below $1!')
        self.assertEqual(option2.position, 10)
        self.assertEqual(option3.value, 'below $10')
        self.assertEqual(option3.position, 100)
        self.assertEqual(option4.value, 'between $10 and $50')
        self.assertEqual(option4.position, 200)
        self.assertEqual(option5.value, '$50+ because you are rich')
        self.assertEqual(option5.position, 300)

    def test_hybrid_ordering(self):
        self.field.option_set.create(position=31415, value='But after a while I got lazy')
        self.field.option_set.create(value='and so I didnt wanna')
        self.field.option_set.create(value='set this ordering')
        self.field.option_set.create(value='anymore')
        self.field.option_set.create(position=42, value='I started this ordering manually')

        option1, option2, option3, option4, option5 = self.field.option_set.all()

        self.assertEqual(option1.value, 'I started this ordering manually')
        self.assertEqual(option1.position, 42)
        self.assertEqual(option2.value, 'But after a while I got lazy')
        self.assertEqual(option2.position, 31415)
        self.assertEqual(option3.value, 'and so I didnt wanna')
        self.assertEqual(option3.position, 31425)
        self.assertEqual(option4.value, 'set this ordering')
        self.assertEqual(option4.position, 31435)
        self.assertEqual(option5.value, 'anymore')
        self.assertEqual(option5.position, 31445)

    def test_position_is_not_nullable(self):
        self.field.option_set.create(position=950, value='950')

        # Noise
        another_field = add_plugin(self.placeholder, 'SelectField', 'en')
        another_field.option_set.create(position=1000, value='1000 for another field so it does not matter')

        option1 = self.field.option_set.create(position=1, value='test')
        option1.position = None
        option1.save()
        self.assertEqual(option1.position, 960)  # We force a value for it on Option.save

        self.assertRaises(IntegrityError, Option.objects.update, position=None)  # See? Not nullable


class FileUploadFieldPluginTest(TestCase):

    def test(self):
        field = FileUploadFieldPlugin(max_size=42)
        self.assertEqual(field.max_size, 42)
        self.assertIsNone(field.enable_js)
        field = FileUploadFieldPlugin(enable_js=True)
        self.assertTrue(field.enable_js)
        self.assertIsNone(field.max_size)
        self.assertIsNone(field.accepted_types)

    def test_accepted_types(self):
        folder = Folder.objects.create(name='Test')
        field = FileUploadFieldPlugin.objects.create(upload_to=folder, accepted_types='.pdf text/plain image/*')
        self.assertIsNone(field.full_clean())

    def test_accepted_types_fails(self):
        folder = Folder.objects.create(name='Test')
        field = FileUploadFieldPlugin.objects.create(upload_to=folder, accepted_types='pdf text')
        with self.assertRaisesMessage(ValidationError, "{'accepted_types': ['pdf text is not mimetype.']}"):
            field.full_clean()


class MultipleFilesUploadFieldPluginTest(TestCase):

    def test(self):
        field = MultipleFilesUploadFieldPlugin(max_size=42)
        self.assertEqual(field.max_size, 42)
        self.assertIsNone(field.enable_js)
        field = MultipleFilesUploadFieldPlugin(enable_js=True)
        self.assertTrue(field.enable_js)
        self.assertIsNone(field.max_size)
        self.assertIsNone(field.accepted_types)

    def test_accepted_types(self):
        folder = Folder.objects.create(name='Test')
        field = MultipleFilesUploadFieldPlugin.objects.create(
            upload_to=folder, accepted_types='.pdf text/plain image/*')
        self.assertIsNone(field.full_clean())

    def test_accepted_types_fails(self):
        folder = Folder.objects.create(name='Test')
        field = MultipleFilesUploadFieldPlugin.objects.create(upload_to=folder, accepted_types='pdf text')
        with self.assertRaisesMessage(ValidationError, "{'accepted_types': ['pdf text is not mimetype.']}"):
            field.full_clean()


class ImageUploadFieldPluginTest(TestCase):

    def test(self):
        field = ImageUploadFieldPlugin(max_size=42)
        self.assertEqual(field.max_size, 42)
        self.assertIsNone(field.enable_js)
        field = ImageUploadFieldPlugin(enable_js=True)
        self.assertTrue(field.enable_js)
        self.assertIsNone(field.max_size)


class FormSubmissionTest(TestCase):

    def setUp(self):
        data = [
            {"label": "Test", "name": "test", "value": 1},
        ]
        self.recipients = [
            {"name": "Dave Lister", "email": "dave@lister.foo"}
        ]
        self.submission = FormSubmission.objects.create(
            name="Test", data=json.dumps(data), recipients = json.dumps(self.recipients))

    def test_form_recipients(self):
        self.assertEqual(self.submission.form_recipients(), self.recipients)

    def test_form_data(self):
        data = [{'name': 'test', 'label': 'Test', 'field_occurrence': 1, 'value': 1}]
        self.assertEqual(self.submission.form_data(), data)


class URLFieldPluginTest(TestCase):

    def test_get_html_id_list(self):
        field = URLFieldPlugin(name="address")
        self.assertEqual(field.get_html_id_list(), "id_address_list")

    def test_empty_list(self):
        field = URLFieldPlugin(name="address")
        self.assertFalse(field.is_list())

    def test_list(self):
        field = URLFieldPlugin(name="address", list="https://example.com")
        self.assertTrue(field.is_list())

    def test_get_list_empty(self):
        field = URLFieldPlugin(name="address")
        self.assertEqual(field.get_list_values_and_labels(), [])

    def test_get_list_str(self):
        field = URLFieldPlugin(name="address", list="")
        self.assertEqual(field.get_list_values_and_labels(), [])

    def test_get_list_spaces(self):
        field = URLFieldPlugin(name="address", list=r"    ")
        self.assertEqual(field.get_list_values_and_labels(), [])

    def test_get_list(self):
        field = URLFieldPlugin(name="address", list="https://example.com")
        self.assertEqual(field.get_list_values_and_labels(), [["https://example.com", None]])

    def test_get_list_more_items(self):
        field = URLFieldPlugin(name="address", list="""
            https://example.com/1/
            https://example.com/2/ Second example
        """)
        self.assertEqual(field.get_list_values_and_labels(), [
            ["https://example.com/1/", None],
            ["https://example.com/2/", "Second example"],
        ])
