from django.http.response import Http404

from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.response import Response

from aldryn_forms.models import FormPlugin, FormSubmission

from .pagination import AldrynFormsPagination
from .permissions import FormPermission, SubmissionsPermission
from .serializers import FormSerializer, FormSubmissionrSerializer


class SubmissionFilter(filters.FilterSet):
    sent_at_period = filters.DateRangeFilter(field_name='sent_at', label="Sent at date range")
    sent_at_range = filters.DateFromToRangeFilter(field_name='sent_at', label="Sent at date from to")
    sent_at_range_time = filters.DateTimeFromToRangeFilter(field_name='sent_at', label="Sent at datetime from to")

    class Meta:
        model = FormSubmission
        fields = ('name', 'language')


class SubmissionsViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = []
    permission_classes = [SubmissionsPermission]
    queryset = FormSubmission.objects.filter(post_ident__isnull=True).order_by('-sent_at')
    serializer_class = FormSubmissionrSerializer
    paginator = AldrynFormsPagination()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = SubmissionFilter

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            data = {"error": {"message": "Object not found."}}
            return Response(data, 400)  # Note: Code 404 cannot be used because it will return a "Not Found page".
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class FormViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = []
    permission_classes = [FormPermission]
    queryset = FormPlugin.objects.all().order_by('name')
    serializer_class = FormSerializer
    paginator = AldrynFormsPagination()
