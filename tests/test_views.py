import json
import sys
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.http import HttpResponseBadRequest
from django.test import modify_settings, override_settings
from django.urls import clear_url_caches

from cms.api import add_plugin, create_page
from cms.appresolver import clear_app_resolvers
from cms.test_utils.testcases import CMSTestCase

from aldryn_forms.models import FormPlugin, FormSubmission, SubmittedToBeSent


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
            # published=True,
            apphook="FormsApp",
        )
        self.placeholder = self.page.get_placeholders("en").get(slot="content")

        self.redirect_url = "http://www.google.com"
        self.redirect_url_with_params = "http://www.google.com?aldryn_form_post_ident=" \
            "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg"

        plugin_data = {
            'redirect_to': {"external_link": self.redirect_url},
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
        public_page = self.page
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

    def test_field_redirect_to_and_success_url(self):
        page = create_page("tpage", "test_page.html", "en", apphook="FormsApp")
        placeholder = page.get_placeholders("en").get(slot="content")
        form_plugin = add_plugin(placeholder, "FormPlugin", "en")
        response = self.client.post(page.get_absolute_url("en"), {"form_plugin_id": form_plugin.id})
        self.assertContains(response, """
            <div class="cms-form-success-message">
                <p>Thank you for submitting your information.</p>
            </div>""", html=True)

    @patch(
        "aldryn_forms.forms.get_random_string",
        lambda length: "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg",
    )
    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    def test_form_view_and_submission_with_apphook_django_gte_111_multiple_steps(self):
        self._form_view_and_submission_with_apphook_django_gte_111(self.redirect_url_with_params)

    def _submit_one_form_instead_multiple(self, redirect_url, form_plugin_name="FormPlugin", post_ident=None):
        """Test checks if only one form is send instead of multiple on page together"""
        page = create_page(
            "multiple forms",
            "test_page.html",
            "en",
            apphook="FormsApp",
        )
        placeholder = page.get_placeholders("en").get(slot="content")

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
            'redirect_to': {"external_link": redirect_url},
        }

        form_plugin2 = add_plugin(placeholder, form_plugin_name, "en", **plugin_data2)  # noqa: E501

        add_plugin(
            placeholder,
            "EmailField",
            "en",
            name="email",
            required=True,
            target=form_plugin2,
            label="Email",
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

        post = {
            "form_plugin_id": form_plugin2.id,
            "email_1": "test@test",
            "email": "test2@test.foo",
        }
        if post_ident is not None:
            post["aldryn_form_post_ident"] = post_ident
        response = self.client.post(page.get_absolute_url("en"), post)
        self.assertRedirects(
            response, plugin_data2["redirect_to"]["external_link"], fetch_redirect_response=False
        )  # noqa: E501

    @patch(
        "aldryn_forms.forms.get_random_string",
        lambda length: "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg",
    )
    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    def test_view_submit_one_form_instead_multiple_multiple_steps(self):
        self._submit_one_form_instead_multiple(self.redirect_url_with_params)
        self.assertQuerySetEqual(SubmittedToBeSent.objects.values_list("name", "data"), [
            ('', '[{"name": "email", "label": "Email", "field_occurrence": 1, "value": "test2@test.foo",'
             ' "plugin_type": "EmailField"}]'),
        ])

    @patch(
        "aldryn_forms.forms.get_random_string",
        lambda length: "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg",
    )
    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    def test_view_append_into_previous_submission(self):
        post_ident = "aBH7hWEGAihsg9KxctpNRfvEXUoOFpJZigmZETqWWNVs4gENFsL3qva1d4Q93URg"
        data = [
            {"label": "Test", "name": "test", "value": 1, "plugin_type": "EmailField"},
        ]
        SubmittedToBeSent.objects.create(name="Test", data=json.dumps(data), post_ident=post_ident)
        self._submit_one_form_instead_multiple(self.redirect_url_with_params, "FormWithIdentPlugin", post_ident)
        self.assertQuerySetEqual(SubmittedToBeSent.objects.values_list("name", "data"), [
            ('Test', '[{"label": "Test", "name": "test", "value": 1, "plugin_type": "EmailField"}, '
             '{"name": "email", "label": "Email", "field_occurrence": 1, "value": "test2@test.foo", '
             '"plugin_type": "EmailField"}]'),
        ])

    def test_view_submit_one_form_instead_multiple(self):
        self._submit_one_form_instead_multiple(self.redirect_url)
        self.assertQuerySetEqual(SubmittedToBeSent.objects.values_list("name", "data"), [])

    def test_view_submit_one_valid_form_instead_multiple(self):
        """Test checks if only one form is validated instead multiple on a page"""
        page = create_page(
            "multiple forms",
            "test_page.html",
            "en",
            apphook="FormsApp",
        )
        placeholder = page.get_placeholders("en").get(slot="content")

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

    def _prepare_form(self, redirect=False, form_plugin_name="FormPlugin"):
        page = create_page(
            "form",
            "test_page.html",
            "en",
            apphook="FormsApp",
        )
        placeholder = page.get_placeholders("en").get(slot="content")

        kwargs = {}
        if redirect:
            kwargs["redirect_to"] = {"internal_link": f"cms.page:{page.pk}"}
        form_plugin = add_plugin(
            placeholder,
            form_plugin_name,
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
        return page, FormPlugin.objects.last(), {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

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
        self.assertEqual(response.json(), {
            'status': 'ERROR',
            'form': {
                '__all__': ['The form could not be submitted. Please check that all form fields are filled in '
                            'correctly.'],
                'email_1': ['This field is required.'],
            }
        })
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
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo", '
             '"plugin_type": "EmailField"}]',)
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
        self.assertContains(response, "<p>Thank you for submitting your information.</p>")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo", '
             '"plugin_type": "EmailField"}]',)
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
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo", '
             '"plugin_type": "EmailField"}]',)
        ], transform=tuple)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0].message()
        self.assertEqual(msg.get("to"), "dave@foo.foo")
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [
            ('[{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test@test.foo", '
             '"plugin_type": "EmailField"}]',)
        ], transform=tuple)

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_form_plugin_is_none(self):
        page, _, _ = self._prepare_form()
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "email_1": "test@test.foo",
            },
        )
        self.assertIsInstance(response, HttpResponseBadRequest)
        self.assertEqual(len(mail.outbox), 0)
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [])

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    def test_middleware_form_error(self):
        page, form_plugin, _ = self._prepare_form(redirect=True)
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
            },
        )
        self.assertEqual(response.context["form"].errors, {
            'email_1': ['This field is required.'],
            '__all__': ['The form could not be submitted. Please check that all form fields are filled in correctly.']
        })
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [])
        self.assertEqual(len(mail.outbox), 0)

    @modify_settings(MIDDLEWARE={"append": "aldryn_forms.middleware.handle_post.HandleHttpPost"})
    @override_settings(ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION=30)
    def test_join_post_into_submission(self):
        page, form_plugin, headers = self._prepare_form(form_plugin_name="FormWithIdentPlugin")
        data = [
            {"label": "Test", "name": "test", "value": 1, "plugin_type": "EmailField"},
        ]
        FormSubmission.objects.create(name="Test submit", data=json.dumps(data), post_ident="1234567890")
        response = self.client.post(
            page.get_absolute_url("en"),
            {
                "form_plugin_id": form_plugin.pk,
                "email_1": "test2@test.foo",
                "aldryn_form_post_ident": "1234567890",
            }, **headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'SUCCESS', 'post_ident': "1234567890", 'message': 'OK'})
        self.assertQuerySetEqual(FormSubmission.objects.values_list('data'), [
            ('[{"label": "Test", "name": "test", "value": 1, "plugin_type": "EmailField"}, '
             '{"name": "email_1", "label": "Submit", "field_occurrence": 1, "value": "test2@test.foo", '
             '"plugin_type": "EmailField"}]',)
        ], transform=tuple)
        self.assertEqual(len(mail.outbox), 0)
