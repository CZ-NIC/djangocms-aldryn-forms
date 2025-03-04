from rest_framework import serializers, viewsets

from aldryn_forms.models import FormSubmission

from .pagination import AldrynFormsPagination


class FormSubmissionrSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FormSubmission
        fields = ['name', 'language', 'sent_at', 'form_recipients', 'form_data']


class SubmissionsViewSet(viewsets.ModelViewSet):
    queryset = FormSubmission.objects.all().order_by('-sent_at')
    serializer_class = FormSubmissionrSerializer
    paginator = AldrynFormsPagination()
