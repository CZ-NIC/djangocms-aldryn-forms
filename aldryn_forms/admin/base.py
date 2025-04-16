import re
from email.utils import formataddr
from typing import Callable
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.sites.models import Site
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from import_export.fields import Field
from import_export.resources import Resource

from ..api.webhook import collect_submissions_data, send_submissions_data
from ..models import FormSubmission, Webhook
from .utils import PrettyJsonEncoder


str_dunder_method = '__str__'


class FieldKey:
    """Field key is pair of names - parent, child."""

    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def __str__(self):
        return "{}+{}".format(self.parent, self.child)


class AldrynFormExportField(Field):
    """AldrynForm export field."""

    def get_value(self, obj):
        if isinstance(self.attribute, FieldKey):
            return obj.get(self.attribute.parent, {}).get(self.attribute.child)
        return obj.get(self.attribute)


class BaseFormSubmissionAdmin(admin.ModelAdmin):
    date_hierarchy = 'sent_at'
    list_display = [
        str_dunder_method, 'sent_at', 'display_honeypot_filled', 'display_post_ident', 'language', 'display_data'
    ]
    list_filter = [
        'name',
        'language',
        'sent_at',
        ("honeypot_filled", admin.BooleanFieldListFilter),
        ("post_ident", admin.BooleanFieldListFilter),
    ]
    search_fields = ["data"]
    actions = ["export_webhook", "send_webhook", "honeypot_filled_on", "honeypot_filled_off"]
    readonly_fields = [
        'name',
        'get_data_for_display',
        'language',
        'sent_at',
        'get_recipients_for_display',
        'post_ident',
        'webhooks',
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name", "get_data_for_display", "language", "sent_at", "webhooks", "form_url", "honeypot_filled"
                ]
            }
        )
    ]

    # (Field name, Field label, json data)
    export_fields = (
        ('name', _('form name'), False),
        ('language', _('form language'), False),
        ('sent_at', _('sent at'), False),
        ('data', _('form data'), True),
        ('recipients', _('users notified'), True),
    )

    class Media:
        css = {
            "all": ["aldryn_forms/css/admin-form.css"],
        }

    def has_add_permission(self, request):
        return False

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        if search_term:
            try:
                re.match(search_term, "")
                queryset |= self.model.objects.filter(data__regex=search_term)
            except Exception as err:
                messages.error(request, err)
        return queryset, may_have_duplicates

    def get_data_for_display(self, obj):
        data = obj.get_form_data()
        html = render_to_string(
            'admin/aldryn_forms/display/submission_data.html',
            {'data': data}
        )
        return html
    get_data_for_display.allow_tags = True
    get_data_for_display.short_description = _('data')

    def get_recipients(self, obj):
        recipients = obj.get_recipients()
        formatted = [formataddr((recipient.name, recipient.email))
                     for recipient in recipients]
        return formatted

    def get_recipients_for_display(self, obj):
        people_list = self.get_recipients(obj)
        html = render_to_string(
            'admin/aldryn_forms/display/recipients.html',
            {'people': people_list},
        )
        return html
    get_recipients_for_display.allow_tags = True
    get_recipients_for_display.short_description = _('people notified')

    def get_urls(self):
        from django.urls import path

        url_patterns = [
            path('export/', self.admin_site.admin_view(self.get_form_export_view()), name=self.get_admin_url('export')),
            path("webhook-export/", self.admin_site.admin_view(self.webhook_export), name="webhook_export"),
            path("webhook-send/", self.admin_site.admin_view(self.webhook_send), name="webhook_send"),
        ]
        return url_patterns + super(BaseFormSubmissionAdmin, self).get_urls()

    def get_admin_url(self, name):
        try:
            model_name = self.model._meta.model_name
        except AttributeError:
            # django <= 1.5 compat
            model_name = self.model._meta.module_name

        url_name = "%s_%s_%s" % (self.model._meta.app_label, model_name, name)
        return url_name

    def get_admin_context(self, form=None, title=None):
        opts = self.model._meta

        context = {
            'media': self.media,
            'has_change_permission': True,
            'opts': opts,
            'root_path': reverse('admin:index'),
            'current_app': self.admin_site.name,
            'app_label': opts.app_label,
        }

        if form:
            context['adminform'] = form
            context['media'] += form.media

        if title:
            context['original'] = title
        return context

    def get_form_export_view(self):
        raise NotImplementedError

    def export_field_parse_data(self, submission):
        """Parse export form field data."""
        fields, values = {}, {}
        for serialized_form_field in submission.get_form_data():
            if serialized_form_field.value:
                fields[serialized_form_field.field_id] = serialized_form_field.label
                values[serialized_form_field.field_id] = serialized_form_field.value
        return fields, values

    def export_field_parse_recipients(self, submission):
        """Parse export form field recipients."""
        fields, values = {'email': _("E-mail")}, {}
        for recipient in submission.get_recipients():
            values['email'] = recipient.email
            if recipient.name:
                values['name'] = recipient.name
                if 'name' not in fields:
                    fields['name'] = _('Name')
        return fields, values

    def export_dataset_and_labels(self, queryset):
        """Collect fields from JSON data."""
        dataset = []
        extra_field_labels = {}
        cols = {name: label for name, label, json_data in self.export_fields}
        unique_codes = []
        for submission in queryset:
            data_item = {}
            for field_name, field_label, field_json_data in self.export_fields:
                field_value = getattr(submission, field_name)
                if field_value is None or field_value == "":
                    continue
                if field_json_data:
                    fnc = getattr(self, "export_field_parse_{}".format(field_name), None)
                    if fnc is not None:
                        field_columns, field_values = fnc(submission)
                        data_item[field_name] = field_values
                        for name, label in field_columns.items():
                            field_key = FieldKey(field_name, name)
                            code = str(field_key)
                            if code not in unique_codes:
                                unique_codes.append(code)
                                if field_name not in extra_field_labels:
                                    extra_field_labels[field_name] = {}
                                extra_field_labels[field_name][field_key] = "{} / {}".format(cols[field_name], label)
                    else:
                        data_item[field_name] = field_value
                else:
                    data_item[field_name] = field_value
            dataset.append(data_item)
        return dataset, extra_field_labels

    def export_data(self, export_type, queryset):
        """Export data into format defined by export_type."""
        extra_field_labels = {}
        dataset, extra_field_labels = self.export_dataset_and_labels(queryset)

        fields = []
        headers = []
        for name, label, json_data in self.export_fields:
            if json_data:
                for code, label in extra_field_labels.get(name, {}).items():
                    fields.append(AldrynFormExportField(attribute=code))
                    headers.append(force_str(label))
            else:
                fields.append(AldrynFormExportField(attribute=name))
                headers.append(force_str(label))

        resource = Resource()
        resource.get_export_headers = lambda: headers
        for field in fields:
            resource.fields[force_str(field.attribute)] = field

        return getattr(resource.export(dataset), export_type)

    @admin.display(description=_("data"))
    def display_data(self, obj) -> str:
        if hasattr(settings, 'ALDRYN_FORMS_SUBMISSION_LIST_DISPLAY_FIELD'):
            submission_field = import_string(settings.ALDRYN_FORMS_SUBMISSION_LIST_DISPLAY_FIELD)
            return submission_field(obj)
        return ''

    @admin.display(boolean=True, description=_("Is spam"))
    def display_honeypot_filled(self, obj) -> bool:
        return obj.honeypot_filled

    @admin.display(boolean=True, description=_("Ready"))
    def display_post_ident(self, obj) -> bool:
        return obj.post_ident is None

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
        if not ids:
            messages.warning(
                request, "Items must be selected in order to perform actions on them. No items have been changed.")
            return HttpResponseRedirect(reverse("admin:aldryn_forms_formsubmission_changelist"))
        submissions = FormSubmission.objects.filter(pk__in=ids.split("."))
        SelectWebhookForm = self.get_select_webhook_form()
        if request.method == "POST":
            if submissions.count():
                form = SelectWebhookForm(request.POST)
                if form.is_valid():
                    webhook = Webhook.objects.get(pk=form.cleaned_data["webhook"])
                    return process_fnc(request, submissions, webhook)
                else:
                    messages.error(request, form.errors.as_text())
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

    @admin.action(description=_("Send data via webhook"), permissions=['change'])
    def send_webhook(self, request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect:
        return self.process_response_redirect(queryset, "admin:webhook_send")

    @admin.action(description=_("Set as spam"), permissions=['change'])
    def honeypot_filled_on(self, request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect:
        queryset.update(honeypot_filled=True)

    @admin.action(description=_("Set not to spam"), permissions=['change'])
    def honeypot_filled_off(self, request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect:
        queryset.update(honeypot_filled=False)
