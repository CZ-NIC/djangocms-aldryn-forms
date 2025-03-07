from django.contrib import admin

from tablib import Dataset

from ..models import FormSubmission, Webook
from .base import BaseFormSubmissionAdmin
from .views import FormExportWizardView


def get_supported_format():
    """Get supported format from types xlsx, xls, tsv or cvs."""
    dataset = Dataset()
    for ext in ('xlsx', 'xls'):
        try:
            getattr(dataset, ext)
            return ext
        except (ImportError, AttributeError):
            pass
    return 'csv'


class FormSubmissionAdmin(BaseFormSubmissionAdmin):
    readonly_fields = BaseFormSubmissionAdmin.readonly_fields + ['form_url']

    def get_form_export_view(self):
        return FormExportWizardView.as_view(admin=self, file_type=get_supported_format())


admin.site.register(FormSubmission, FormSubmissionAdmin)
admin.site.register(Webook)
