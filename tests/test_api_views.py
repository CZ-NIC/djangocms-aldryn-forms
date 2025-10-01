import json
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.db.utils import NotSupportedError
from django.test import RequestFactory, TestCase

from freezegun import freeze_time

from aldryn_forms.api.views import FormViewSet, SubmissionsViewSet
from aldryn_forms.models import FormPlugin, FormSubmission


class DataMixin:

    def setUp(self):
        self.user = get_user_model().objects.create(username="admin", is_superuser=True)
        self.unauthorized_request = RequestFactory().request()
        self.request = RequestFactory().request()
        self.request._user = self.user


class FormViewSetTest(DataMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.view = FormViewSet.as_view({"get": "list"})

    def test_forbidden(self):
        response = self.view(self.unauthorized_request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")

    def test_response(self):
        FormPlugin.objects.create(name="Form")
        try:
            response = self.view(self.request)
        except NotSupportedError as err:
            print(err)
            print("Use a different database for this FormViewSetTest.test_response.")
            return
        data = {"count": 1, "next": None, "previous": None, "results": [{"name": "Form"}]}
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, data)


@freeze_time(datetime(2025, 3, 14, 9, 30, tzinfo=timezone.utc))
class SubmissionsViewSetTest(DataMixin, TestCase):

    submitted_post = {
        "hostname": "example.com",
        "name": "Test submit",
        "language": "en",
        "sent_at": "2025-03-14T04:30:00-05:00",
        "form_recipients": [],
        "form_data": [{
            "name": "test",
            "label": "Test",
            "field_occurrence": 1,
            "value": 1,
            "plugin_type": "TextField",
            }]
        }
    submitted_posts_list = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            submitted_post
        ]
    }

    def setUp(self):
        super().setUp()
        self.view = SubmissionsViewSet.as_view({"get": "list"})

    def test_forbidden(self):
        response = self.view(self.unauthorized_request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")

    def test_response(self):
        data = [
            {"label": "Test", "name": "test", "value": 1, "plugin_type": "TextField"},
        ]
        FormSubmission.objects.create(name="Test submit", data=json.dumps(data))
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.submitted_posts_list)

    def test_get_object(self):
        data = [
            {"label": "Test", "name": "test", "value": 1, "plugin_type": "TextField"},
        ]
        submission = FormSubmission.objects.create(name="Test submit", data=json.dumps(data))
        view = SubmissionsViewSet.as_view({"get": "retrieve"})
        response = view(self.request, pk=submission.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.submitted_post)

    def test_get_object_not_found(self):
        view = SubmissionsViewSet.as_view({"get": "retrieve"})
        response = view(self.request, pk=42)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"error": {"message": "Object not found."}})
