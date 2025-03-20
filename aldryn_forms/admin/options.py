from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

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


class SelectWebhookForm(forms.Form):
    webhook = forms.ChoiceField(choices=Webhook.objects.values_list("pk", "name").order_by("name"))


class FormSubmissionAdmin(BaseFormSubmissionAdmin):
    readonly_fields = BaseFormSubmissionAdmin.readonly_fields + ['form_url']
    search_fields = ["data"]
    actions = ["export_webhook"]

    def get_form_export_view(self):
        return FormExportWizardView.as_view(admin=self, file_type=get_supported_format())

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        queryset |= self.model.objects.filter(data__regex=search_term)
        return queryset, may_have_duplicates

    def get_urls(self):
        urls = super().get_urls()
        return [
            path("webhook-export/", self.admin_site.admin_view(self.webhook_export), name="webhook_export")
        ] + urls

    def export_submissions_by_webhook(self, request, submissions, webhook):
        messages.success(request, "OK")
        return HttpResponseRedirect(reverse("admin:aldryn_forms_formsubmission_changelist"))

    def webhook_export(self, request):
        ids = request.GET.get("ids", "")
        submissions = FormSubmission.objects.filter(pk__in=ids.split("."))
        if request.method == "POST":
            if submissions.count():
                form = SelectWebhookForm(request.POST)
                if form.is_valid():
                    try:
                        webhook = Webhook.objects.get(pk=form.cleaned_data["webhook"])
                    except Webhook.DoesNotExist as err:
                        messages.error(request, err)
                    else:
                        return self.export_submissions_by_webhook(request, submissions, webhook)
            else:
                messages.error(request, _("Missing items for processing."))
            return HttpResponseRedirect(reverse("admin:aldryn_forms_formsubmission_changelist"))
        else:
            form = SelectWebhookForm()
        data = {
            "ids": ids,
            "form": form,
            "submissins_size": submissions.count(),
        }
        context = dict(self.admin_site.each_context(request), **data)
        return TemplateResponse(request, "admin/aldryn_forms/formsubmission/webhook_form.html", context)

    @admin.action(description='Export formatted by webhook', permissions=['change'])
    def export_webhook(self, request, queryset):
        selected = queryset.values_list("pk", flat=True)
        params = urlencode({"ids": ".".join([str(pk) for pk in selected])})
        path = reverse("admin:webhook_export")
        return HttpResponseRedirect(f"{path}?{params}")
    export_webhook.short_description = 'Export formatted by webhook'


class WebhookAdmin(admin.ModelAdmin):
    form = WebhookAdminForm
