import json

from django.test import TestCase

from aldryn_forms.admin.forms import WebhookAdminForm
from aldryn_forms.models import Webhook


class Form(WebhookAdminForm):
    class Meta:
        model = Webhook
        fields = "__all__"


class WebhookAdminFormTest(TestCase):

    post = {
        "name": "Test",
        "url": "https://example.com/",
        "method": "post",
    }

    def _get_post(self, data):
        post = self.post.copy()
        post["transform"] = json.dumps(data)
        return post

    def test_required(self):
        form = Form({})
        self.assertEqual(form.errors, {
            'name': ['This field is required.'],
            'url': ['This field is required.'],
            'method': ['This field is required.']
        })

    def test_data(self):
        form = Form(self.post)
        self.assertTrue(form.is_valid())

    def test_not_type_array(self):
        form = Form(self._get_post({}))
        self.assertEqual(form.errors, {'transform': ["{} is not of type 'array'"]})

    def test_not_type_object(self):
        form = Form(self._get_post([1]))
        self.assertEqual(form.errors, {'transform': ["1 is not of type 'object'"]})

    def test_missing_dest(self):
        form = Form(self._get_post([{}]))
        self.assertEqual(form.errors, {'transform': ["'dest' is a required property"]})

    def test_invalid_schema(self):
        form = Form(self._get_post([{"dest": "name"}]))
        self.assertEqual(form.errors, {'transform': ["{'dest': 'name'} is not valid under any of the given schemas"]})

    def test_item_with_value(self):
        form = Form(self._get_post([{"dest": "name", "value": "42"}]))
        self.assertTrue(form.is_valid())

    def test_item_with_fnc(self):
        form = Form(self._get_post([{"dest": "name", "fnc": "module.path.name"}]))
        self.assertTrue(form.is_valid())

    def test_item_with_src(self):
        form = Form(self._get_post([{"dest": "name", "src": ".name"}]))
        self.assertTrue(form.is_valid())
