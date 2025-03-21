import re
from typing import Callable
from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.contrib.sites.models import Site
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from tablib import Dataset

from ..api.webhook import collect_submissions_data, send_submissions_data
from ..models import FormSubmission, Webhook
from .base import BaseFormSubmissionAdmin
from .forms import WebhookAdminForm
from .utils import PrettyJsonEncoder
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
    actions = ["export_webhook", "send_webhook"]

    def get_form_export_view(self):
        return FormExportWizardView.as_view(admin=self, file_type=get_supported_format())

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        try:
            re.match(search_term, "")
            queryset |= self.model.objects.filter(data__regex=search_term)
        except Exception:
            pass
        return queryset, may_have_duplicates

    def get_urls(self):
        urls = super().get_urls()
        return [
            path("webhook-export/", self.admin_site.admin_view(self.webhook_export), name="webhook_export"),
            path("webhook-send/", self.admin_site.admin_view(self.webhook_send), name="webhook_send"),
        ] + urls

    def get_select_webhook_form(self) -> forms.Form:
        return type("SelectWebhookForm", (forms.Form,), {
            "webhook": forms.ChoiceField(choices=Webhook.objects.values_list("pk", "name").order_by("name")),
        })

    def export_submissions_by_webhook(
        self, request: HttpRequest, submissions: FormSubmission, webhook: Webhook
    ) -> JsonResponse:
        site = Site.objects.first()
        data = collect_submissions_data(webhook, submissions, site.domain)
        response = JsonResponse({"data": data}, encoder=PrettyJsonEncoder, json_dumps_params={"ensure_ascii": False})
        filename = f"form-submissions-webhook-{slugify(webhook.name)}.json"
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def send_submissions_data(
        self, request: HttpRequest, submissions: FormSubmission, webhook: Webhook
    ) -> HttpResponseRedirect:
        site = Site.objects.first()
        send_submissions_data(webhook, submissions, site.domain)
        messages.success(request, _("Data sending completed."))
        return HttpResponseRedirect(reverse("admin:aldryn_forms_formsubmission_changelist"))

    def process_webhook(self, request: HttpRequest, process_fnc: Callable, process_title: str) -> HttpResponse:
        ids = request.GET.get("ids", "")
        submissions = FormSubmission.objects.filter(pk__in=ids.split("."))
        SelectWebhookForm = self.get_select_webhook_form()
        if request.method == "POST":
            if submissions.count():
                form = SelectWebhookForm(request.POST)
                if form.is_valid():
                    try:
                        webhook = Webhook.objects.get(pk=form.cleaned_data["webhook"])
                    except Webhook.DoesNotExist as err:
                        messages.error(request, err)
                    else:
                        return process_fnc(request, submissions, webhook)
            else:
                messages.error(request, _("Missing items for processing."))
            return HttpResponseRedirect(reverse("admin:aldryn_forms_formsubmission_changelist"))
        else:
            form = SelectWebhookForm()
        data = {
            "ids": ids,
            "form": form,
            "submissins_size": submissions.count(),
            "process_title": process_title,
        }
        context = dict(self.admin_site.each_context(request), **data)
        return TemplateResponse(request, "admin/aldryn_forms/formsubmission/webhook_form.html", context)

    def webhook_export(self, request: HttpRequest) -> HttpResponse:
        return self.process_webhook(request, self.export_submissions_by_webhook, _("Export data via webhook"))

    def webhook_send(self, request: HttpRequest) -> HttpResponse:
        return self.process_webhook(request, self.send_submissions_data, _("Send data via webhook"))

    def process_response_redirect(self, queryset: QuerySet, path_name: str) -> HttpResponseRedirect:
        selected = queryset.values_list("pk", flat=True)
        params = urlencode({"ids": ".".join([str(pk) for pk in selected])})
        path = reverse(path_name)
        return HttpResponseRedirect(f"{path}?{params}")

    @admin.action(description=_("Export data via webhook"), permissions=['change'])
    def export_webhook(self, request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect:
        return self.process_response_redirect(queryset, "admin:webhook_export")
    export_webhook.short_description = _("Export data via webhook")

    @admin.action(description=_("Send data via webhook"), permissions=['change'])
    def send_webhook(self, request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect:
        return self.process_response_redirect(queryset, "admin:webhook_send")
    send_webhook.short_description = _("Send data via webhook")


class WebhookAdmin(admin.ModelAdmin):
    form = WebhookAdminForm
