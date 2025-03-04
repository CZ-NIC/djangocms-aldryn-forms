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
    sent_at_period = filters.DateRangeFilter(field_name='sent_at', label="Sent at date range")
    sent_at_range = filters.DateFromToRangeFilter(field_name='sent_at', label="Sent at date from to")
    sent_at_range_time = filters.DateTimeFromToRangeFilter(field_name='sent_at', label="Sent at datetime from to")

    class Meta:
        model = FormSubmission
        fields = ('name', 'language')


class SubmissionsViewSet(viewsets.ModelViewSet):
    authentication_classes = []
    permission_classes = [SubmissionsPermission]
    queryset = FormSubmission.objects.filter(post_ident__isnull=True).order_by('-sent_at')
    serializer_class = FormSubmissionrSerializer
    paginator = AldrynFormsPagination()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = SubmissionFilter
