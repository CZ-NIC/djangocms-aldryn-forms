from django.conf import settings
from django.contrib import admin
from django.template.loader import render_to_string

from tablib import Dataset

from ..models import FormSubmission, Webhook
from .base import BaseFormSubmissionAdmin
from .forms import WebhookAdminForm
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


def display_form_submission_data(instance: FormSubmission) -> str:
    context = {"data": instance.get_form_data()}
    return render_to_string("admin/aldryn_forms/display/submission_display_fields.html", context)


class FormSubmissionAdmin(BaseFormSubmissionAdmin):
    readonly_fields = BaseFormSubmissionAdmin.readonly_fields + ['form_url']

    def get_form_export_view(self):
        return FormExportWizardView.as_view(admin=self, file_type=get_supported_format())


class WebhookAdmin(admin.ModelAdmin):
    form = WebhookAdminForm

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["SITE_API_ROOT"] = getattr(settings, "SITE_API_ROOT", "")
        return super().changeform_view(request, object_id, form_url, extra_context)


admin.site.register(FormSubmission, FormSubmissionAdmin)
admin.site.register(Webhook, WebhookAdmin)
