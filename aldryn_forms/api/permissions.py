from rest_framework.permissions import BasePermission


class SubmissionsPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user.has_perm("aldryn_forms.view_formsubmission")


class FormPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user.has_perm("aldryn_forms.view_formplugin")
