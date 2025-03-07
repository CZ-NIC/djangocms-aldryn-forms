from rest_framework import serializers

from aldryn_forms.models import FormPlugin, FormSubmission


class FormSubmissionSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = FormSubmission
        fields = ['name', 'language', 'sent_at', 'form_recipients', 'form_data']


class FormSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = FormPlugin
        fields = ['name']
