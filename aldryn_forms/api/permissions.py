from typing import TYPE_CHECKING

from django.http import HttpRequest

from rest_framework.permissions import BasePermission


if TYPE_CHECKING:  # pragma: no cover
    from .views import FormViewSet, SubmissionsViewSet


class SubmissionsPermission(BasePermission):

    def has_permission(self, request: HttpRequest, view: "SubmissionsViewSet") -> bool:
        return request.user.has_perm("aldryn_forms.view_formsubmission")


class FormPermission(BasePermission):

    def has_permission(self, request: HttpRequest, view: "FormViewSet") -> bool:
        return request.user.has_perm("aldryn_forms.view_formplugin")
