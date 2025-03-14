from django.test import RequestFactory, TestCase

from aldryn_forms.api.views import FormViewSet, SubmissionsViewSet


class FormViewSetTest(TestCase):

    def setUp(self):
        self.view = FormViewSet.as_view({'get': 'list'})
        self.request = RequestFactory().request()

    def test_forbidden(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")


class SubmissionsViewSetTest(TestCase):

    def setUp(self):
        self.view = SubmissionsViewSet.as_view({'get': 'list'})
        self.request = RequestFactory().request()

    def test_forbidden(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")
