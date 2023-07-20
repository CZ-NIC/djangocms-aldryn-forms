from email.utils import formataddr

from django.contrib import admin
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from import_export.fields import Field
from import_export.resources import Resource


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
    list_display = [str_dunder_method, 'sent_at', 'language']
    list_filter = ['name', 'language']
    readonly_fields = [
        'name',
        'get_data_for_display',
        'language',
        'sent_at',
        'get_recipients_for_display',
    ]

    # (Field name, Field label, json data)
    export_fields = (
        ('name', _('form name'), False),
        ('language', _('form language'), False),
        ('sent_at', _('sent at'), False),
        ('data', _('form data'), True),
        ('recipients', _('users notified'), True),
    )

    def has_add_permission(self, request):
        return False

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
