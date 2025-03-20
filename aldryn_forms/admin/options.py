from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from tablib import Dataset

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


class FormSubmissionAdmin(BaseFormSubmissionAdmin):
    readonly_fields = BaseFormSubmissionAdmin.readonly_fields + ['form_url']
    search_fields = ["data"]

    def get_form_export_view(self):
        return FormExportWizardView.as_view(admin=self, file_type=get_supported_format())

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        queryset |= self.model.objects.filter(data__regex=search_term)
        return queryset, may_have_duplicates

    def get_urls(self):
        urls = super().get_urls()
        return [
            path("webhooks-export/", self.admin_site.admin_view(self.webhook_export), name="webhook_export")
        ] + urls

    def webhook_export(self, request):
        # http://localhost:8222/en/admin/aldryn_forms/formsubmission/webhooks-export/
        form = None
        context = dict(self.admin_site.each_context(request), form=form)
        return TemplateResponse(request, "admin/aldryn_forms/formsubmission/webhook_form.html", context)


class WebhookAdmin(admin.ModelAdmin):
    form = WebhookAdminForm
