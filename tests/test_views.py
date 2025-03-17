import sys
from distutils.version import LooseVersion
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import modify_settings, override_settings
from django.urls import clear_url_caches

import cms
from cms.api import add_plugin, create_page
from cms.appresolver import clear_app_resolvers
from cms.test_utils.testcases import CMSTestCase

from aldryn_forms.models import FormSubmission


# These means "less than or equal"
CMS_3_6 = LooseVersion(cms.__version__) < LooseVersion("4.0")


class SubmitFormViewTest(CMSTestCase):

    def setUp(self):
        self.APP_MODULE = "aldryn_forms.cms_apps.FormsApp"
        clear_app_resolvers()
        clear_url_caches()

        if self.APP_MODULE in sys.modules:
            del sys.modules[self.APP_MODULE]

        self.page = create_page(
            "tpage",
            "test_page.html",
            "en",
            published=True,
            apphook="FormsApp",
        )
        try:
            self.placeholder = self.page.placeholders.get(slot="content")
        except AttributeError:
            self.placeholder = self.page.get_placeholders("en").get(slot="content")

        self.redirect_url = "http://www.google.com"
        self.redirect_url_with_params = "http://www.google.com?aldryn_form_post_ident=" \
            "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg"

        plugin_data = {
            "redirect_type": "redirect_to_url",
            "url": self.redirect_url,
        }
        self.form_plugin = add_plugin(
            self.placeholder, "FormPlugin", "en", **plugin_data
        )  # noqa: E501

        add_plugin(
            self.placeholder,
            "SubmitButton",
            "en",
            target=self.form_plugin,
            label="Submit",
        )
        self.form_plugin.action_backend = "default"
        self.form_plugin.save()
        if CMS_3_6:
            self.page.publish("en")

        self.reload_urls()
        self.apphook_clear()

    def tearDown(self):
        clear_app_resolvers()
        clear_url_caches()

        if self.APP_MODULE in sys.modules:
            del sys.modules[self.APP_MODULE]

        self.reload_urls()
        self.apphook_clear()

    def reload_urls(self):
        from django.conf import settings

        url_modules = [
            "cms.urls",
            self.APP_MODULE,
            settings.ROOT_URLCONF,
        ]

        clear_app_resolvers()
        clear_url_caches()

        for module in url_modules:
            if module in sys.modules:
                del sys.modules[module]

    def _form_view_and_submission_with_apphook_django_gte_111(self, redirect_url):
        if CMS_3_6:
            public_page = self.page.publisher_public
        else:
            public_page = self.page
        try:
            public_placeholder = public_page.placeholders.first()
        except AttributeError:
            public_placeholder = public_page.get_placeholders("en").first()

        public_page_form_plugin = public_placeholder.cmsplugin_set.filter(
            plugin_type="FormPlugin"
        ).first()
        response = self.client.get(self.page.get_absolute_url("en"))

        input_string = '<input type="hidden" name="form_plugin_id" value="{}"'
        self.assertContains(response, input_string.format(public_page_form_plugin.id))  # noqa: E501

        response = self.client.post(
            self.page.get_absolute_url("en"),
            {
                "form_plugin_id": public_page_form_plugin.id,
            },
        )
        self.assertRedirects(
            response, redirect_url, fetch_redirect_response=False
        )  # noqa: E501

    def test_form_view_and_submission_with_apphook_django_gte_111(self):
        self._form_view_and_submission_with_apphook_django_gte_111(self.redirect_url)

    @patch(
        "aldryn_forms.forms.get_random_string",
        lambda length: "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg",
    )
    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    def test_form_view_and_submission_with_apphook_django_gte_111_multiple_steps(self):
        self._form_view_and_submission_with_apphook_django_gte_111(self.redirect_url_with_params)

    def _submit_one_form_instead_multiple(self, redirect_url):
        """Test checks if only one form is send instead of multiple on page together"""
        page = create_page(
            "multiple forms",
            "test_page.html",
            "en",
            published=True,
            apphook="FormsApp",
        )
        placeholder = page.placeholders.get(slot="content")

        form_plugin = add_plugin(
            placeholder,
            "FormPlugin",
            "en",
        )  # noqa: E501

        add_plugin(
            placeholder,
            "EmailField",
            "en",
            name="email_1",
            required=True,
            target=form_plugin,
            label="Submit",
        )

        add_plugin(
            placeholder,
            "SubmitButton",
            "en",
            target=form_plugin,
            label="Submit",
        )

        form_plugin.action_backend = "default"
        form_plugin.save()

        plugin_data2 = {
            "redirect_type": "redirect_to_url",
            "url": redirect_url,
        }

        form_plugin2 = add_plugin(placeholder, "FormPlugin", "en", **plugin_data2)  # noqa: E501

        add_plugin(
            placeholder,
            "SubmitButton",
            "en",
            target=form_plugin2,
            label="Submit",
        )

        form_plugin2.action_backend = "default"
        form_plugin2.save()

        page.publish("en")
        self.reload_urls()
        self.apphook_clear()

        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin2.id,
                "email_1": "test@test",
            },
        )
        self.assertRedirects(
            response, plugin_data2["url"], fetch_redirect_response=False
        )  # noqa: E501

    @patch(
        "aldryn_forms.forms.get_random_string",
        lambda length: "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg",
    )
    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    def test_view_submit_one_form_instead_multiple_multiple_steps(self):
        self._submit_one_form_instead_multiple(self.redirect_url_with_params)

    def test_view_submit_one_form_instead_multiple(self):
        self._submit_one_form_instead_multiple(self.redirect_url)

    def test_view_submit_one_valid_form_instead_multiple(self):
        """Test checks if only one form is validated instead multiple on a page"""
        page = create_page(
            "multiple forms",
            "test_page.html",
            "en",
            published=True,
            apphook="FormsApp",
        )
        placeholder = page.placeholders.get(slot="content")

        form_plugin = add_plugin(
            placeholder,
            "FormPlugin",
            "en",
        )  # noqa: E501

        add_plugin(
            placeholder,
            "EmailField",
            "en",
            name="email_1",
            required=True,
            target=form_plugin,
        )

        add_plugin(
            placeholder,
            "SubmitButton",
            "en",
            target=form_plugin,
            label="Submit",
        )

        form_plugin.action_backend = "default"
        form_plugin.save()

        form_plugin2 = add_plugin(
            placeholder,
            "FormPlugin",
            "en",
        )  # noqa: E501

        add_plugin(
            placeholder,
            "EmailField",
            "en",
            name="email_2",
            required=True,
            target=form_plugin2,
        )

        add_plugin(
            placeholder,
            "SubmitButton",
            "en",
            target=form_plugin2,
            label="Submit",
        )

        form_plugin2.action_backend = "default"
        form_plugin2.save()

        page.publish("en")
        self.reload_urls()
        self.apphook_clear()

        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin2.id,
                "email_2": "test@test",
            },
        )

        email_field = '<input type="email" name="{name}"'
        self.assertContains(response, email_field.format(name="email_1"))
        self.assertContains(response, email_field.format(name="email_2"))

    def _prepare_form(self, redirect=False):
        page = create_page(
            "form",
            "test_page.html",
            "en",
            published=True,
            apphook="FormsApp",
        )
        placeholder = page.placeholders.get(slot="content")

        kwargs = {}
        if redirect:
            kwargs["redirect_type"] = "redirect_to_page"
            kwargs["redirect_page"] =  page
            # kwargs["success_url"] = "https://test.foo/success/"
        form_plugin = add_plugin(
            placeholder,
            "FormPlugin",
            "en",
            action_backend="default",
            **kwargs
        )  # noqa: E501
        user = get_user_model().objects.create(username="Dave", email="dave@foo.foo")
        form_plugin.recipients.add(user)

        add_plugin(
            placeholder,
            "EmailField",
            "en",
            name="email_1",
            required=True,
            target=form_plugin,
            label="Submit",
        )
        page.publish("en")
        self.reload_urls()
        self.apphook_clear()
        return page, form_plugin, {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_method_get(self):
        page, form_plugin, headers = self._prepare_form()
        response = self.client.get(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
                "email_1": "test@test",
            }, **headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [])
        self.assertEqual(len(mail.outbox), 0)

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_method_invalid_id(self):
        page, _, headers = self._prepare_form()
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": "foo",
                "email_1": "test@test",
            }, **headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [])
        self.assertEqual(len(mail.outbox), 0)

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_method_unknown_id(self):
        page, _, headers = self._prepare_form()
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": 42,
                "email_1": "test@test",
            }, **headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [])
        self.assertEqual(len(mail.outbox), 0)

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_form_error_json(self):
        page, form_plugin, headers = self._prepare_form()
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
            }, **headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ERROR', 'form': {'email_1': ['This field is required.']}})
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [])
        self.assertEqual(len(mail.outbox), 0)

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_success_json(self):
        page, form_plugin, headers = self._prepare_form()
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
                "email_1": "test@test.foo",
            }, **headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'SUCCESS', 'post_ident': None, 'message': 'OK'})
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo"}]',)
        ], transform=tuple)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_success(self):
        page, form_plugin, _ = self._prepare_form()
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
                "email_1": "test@test.foo",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/html; charset=utf-8")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo"}]',)
        ], transform=tuple)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_success_redirect(self):
        page, form_plugin, _ = self._prepare_form(redirect=True)
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
                "email_1": "test@test.foo",
            },
        )
        self.assertRedirects(response, page.get_absolute_url("en"))
        self.assertEqual(response.get("Content-Type"), "text/html; charset=utf-8")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo"}]',)
        ], transform=tuple)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")
