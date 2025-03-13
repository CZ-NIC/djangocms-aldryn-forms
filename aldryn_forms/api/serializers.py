from rest_framework import serializers

from aldryn_forms.models import FormPlugin, FormSubmission


class FormSubmissionSerializer(serializers.HyperlinkedModelSerializer):

    hostname = serializers.SerializerMethodField('set_hostname')

    class Meta:
        model = FormSubmission
        fields = ['hostname', 'name', 'language', 'sent_at', 'form_recipients', 'form_data']

    def set_hostname(self, instance: FormSubmission) -> str:
        return self.context.get("hostname", "testserver")


class FormSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = FormPlugin
        fields = ['name']
