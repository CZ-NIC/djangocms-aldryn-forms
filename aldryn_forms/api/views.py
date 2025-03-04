from django_filters import rest_framework as filters
from rest_framework import serializers, viewsets
from rest_framework.permissions import BasePermission

from aldryn_forms.models import FormSubmission

from .pagination import AldrynFormsPagination


class SubmissionsPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user.has_perm("aldryn_forms.view_formsubmission")


class FormSubmissionrSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FormSubmission
        fields = ['name', 'language', 'sent_at', 'form_recipients', 'form_data']


class SubmissionFilter(filters.FilterSet):
    class Meta:
        model = FormSubmission
        fields = ('name', 'sent_at')


class SubmissionsViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [SubmissionsPermission]
    queryset = FormSubmission.objects.all().order_by('-sent_at')
    serializer_class = FormSubmissionrSerializer
    paginator = AldrynFormsPagination()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = SubmissionFilter
