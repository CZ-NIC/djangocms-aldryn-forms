from django.test import SimpleTestCase, TestCase, override_settings

from aldryn_forms.models import SerializedFormField
from aldryn_forms.templatetags.aldryn_forms_admin_tags import display_field_value, make_link, media_filer_public_link


class MakeLinkTest(SimpleTestCase):

    def test_make_link(self):
        link = make_link("https://localhost/path/to/file.txt", "example.com")
        self.assertEqual(
            link, '<a href="https://example.com/path/to/file.txt" '
            'title="https://localhost/path/to/file.txt" target="_blank">file.txt</a>')

    @override_settings(ALDRYN_FORMS_URL_SCHEME="http")
    def test_overwrite_scheme(self):
        link = make_link("https://localhost/path/to/file.txt", "example.com")
        self.assertEqual(
            link, '<a href="http://example.com/path/to/file.txt" '
            'title="https://localhost/path/to/file.txt" target="_blank">file.txt</a>')


class DisplayFieldValueTest(TestCase):

    def test_plugin_type(self):
        field = SerializedFormField(
            "attachments",
            "Attachments",
            1,
            "\n".join((
                "https://localhost/path/to/file1.txt",
                "https://localhost/path/to/file2.txt",
            )),
            "MultipleFilesField")
        links = display_field_value(field)
        self.assertEqual(
            links,
            "\n".join((
                '<a href="https://example.com/path/to/file1.txt" title="https://localhost/path/to/file1.txt" '
                'target="_blank">file1.txt</a>',
                '<a href="https://example.com/path/to/file2.txt" title="https://localhost/path/to/file2.txt" '
                'target="_blank">file2.txt</a>',
            ))
        )

    def test_without_plugin_type(self):
        field = SerializedFormField(
            "attachments",
            "Attachments",
            1,
            "\n".join((
                "https://example.com/media/filer_public/file1.txt",
                "https://example.com/smedia/filer_private/file2.txt",
                "https://localhost/path/to/file3.txt",
            )),
            "")
        links = display_field_value(field)
        self.assertEqual(
            links,
            "\n".join((
                '<a href="https://example.com/media/filer_public/file1.txt" '
                'title="https://example.com/media/filer_public/file1.txt" target="_blank">file1.txt</a>',
                '<a href="https://example.com/smedia/filer_private/file2.txt" '
                'title="https://example.com/smedia/filer_private/file2.txt" target="_blank">file2.txt</a>',
                'https://localhost/path/to/file3.txt'
            ))
        )


class MediaFilerPublicLinkTest(TestCase):

    def test(self):
        value = "\n".join((
            "https://example.com/media/filer_public/file1.txt",
            "https://example.com/smedia/filer_private/file2.txt",
            "https://localhost/path/to/file3.txt",
        ))
        links = media_filer_public_link(value)
        self.assertEqual(
            links,
            "\n".join((
                '<a href="https://example.com/media/filer_public/file1.txt" '
                'title="https://example.com/media/filer_public/file1.txt" target="_blank">file1.txt</a>',
                '<a href="https://example.com/smedia/filer_private/file2.txt" '
                'title="https://example.com/smedia/filer_private/file2.txt" target="_blank">file2.txt</a>',
                'https://localhost/path/to/file3.txt'
            ))
        )
