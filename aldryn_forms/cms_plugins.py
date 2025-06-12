import logging
import re
import smtplib
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import TabularInline
from django.core.validators import MinLengthValidator
from django.db.models import query
from django.http import HttpRequest
from django.template.loader import select_template
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, gettext
from django.utils.translation import gettext_lazy as _

from cms.models.pluginmodel import CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from cms.plugin_rendering import PluginContext

import markdown
from emailit.api import send_mail
from emailit.utils import get_template_names
from filer.models import filemodels, imagemodels
from PIL import Image

from . import models
from .constants import (
    ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, ALDRYN_FORMS_POST_IDENT_NAME, EMAIL_REPLY_TO, MAX_IDENT_SIZE,
)
from .forms import (
    BooleanFieldForm, CaptchaFieldForm, DateFieldForm, DateTimeFieldForm, EmailFieldForm, FileFieldForm, FormPluginForm,
    FormSubmissionBaseForm, HiddenFieldForm, ImageFieldForm, MultipleSelectFieldForm, RadioFieldForm,
    RestrictedFileField, RestrictedImageField, RestrictedMultipleFilesField, SelectFieldForm, TextAreaFieldForm,
    TextFieldForm, TimeFieldForm,
)
from .helpers import get_user_name
from .models import FieldPluginBase, SerializedFormField, SubmittedToBeSent
from .signals import form_post_save, form_pre_save
from .sizefield.utils import filesizeformat
from .utils import get_action_backends
from .validators import MaxChoicesValidator, MinChoicesValidator, is_valid_recipient


logger = logging.getLogger(__name__)


class FormElement(CMSPluginBase):
    # Don't cache anything.
    cache = False
    module = _('Forms')


class FieldContainer(FormElement):
    allow_children = True


class FormPlugin(FieldContainer):
    render_template = True
    name = _('Form')
    module = _('Form types')
    model = models.FormPlugin
    form = FormPluginForm
    filter_horizontal = ['recipients']
    ident_field_name = None
    honeypot_filled = False

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'redirect_type',
                'redirect_page',
                'url',
                'use_form_action',
            )
        }),
        (_('Advanced Settings'), {
            'classes': ('collapse',),
            'fields': (
                'form_template',
                'error_message',
                'success_message',
                'recipients',
                'action_backend',
                'webhooks',
                'custom_classes',
                'form_attributes',
            )
        }),
    )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        request = context['request']

        form = self.process_form(instance, request)

        if request.POST.get('form_plugin_id') == str(instance.id) and form.is_valid():
            context['post_success'] = True
            context['form_success_url'] = self.get_success_url(instance, form.instance.post_ident)
        context['form'] = form
        return context

    def get_render_template(self, context, instance, placeholder):
        return instance.form_template

    def form_valid(self, instance: models.FormPlugin, request: HttpRequest, form: FormSubmissionBaseForm) -> Any:
        action_backend = get_action_backends()[form.form_plugin.action_backend]()
        return action_backend.form_valid(self, instance, request, form)

    def form_invalid(self, instance: models.FormPlugin, request: HttpRequest, form: FormSubmissionBaseForm) -> None:
        if instance.error_message:
            form._add_error(message=instance.error_message)

    def process_form(self, instance: models.FormPlugin, request: HttpRequest) -> FormSubmissionBaseForm:
        PROCESSED_FORM = "aldryn_forms_processed_forms"
        processed_forms_dict = getattr(request, PROCESSED_FORM, {})
        processed_form = processed_forms_dict.get(instance.pk)
        if processed_form is not None:
            return processed_form  # Form was already processed by middleware HandleHttpPost.

        form_class = self.get_form_class(instance)
        form_kwargs = self.get_form_kwargs(instance, request)
        form = form_class(**form_kwargs)  # django.forms.widgets.AldrynDynamicForm
        form.ident_field_name = self.ident_field_name

        processed_forms_dict[instance.pk] = form
        setattr(request, PROCESSED_FORM, processed_forms_dict)

        # Put files into fields.
        if form.files:
            for input_name in form.files.keys():
                if input_name in form.fields:
                    form.fields[input_name].files = form.files.getlist(input_name)

        if request.POST.get('form_plugin_id') == str(instance.id) and form.is_valid():
            if self.ident_field_name:
                form.cleaned_data[self.ident_field_name] = request.POST.get(self.ident_field_name, "")[:MAX_IDENT_SIZE]
            fields = [field for field in form.base_fields.values()
                      if hasattr(field, '_plugin_instance')]

            form.instance.honeypot_filled = self.honeypot_filled

            # pre save field hooks
            for field in fields:
                field._plugin_instance.form_pre_save(
                    instance=field._model_instance,
                    form=form,
                    request=request,
                )

            form_pre_save.send(
                sender=models.FormPlugin,
                instance=instance,
                form=form,
                request=request,
            )

            self.form_valid(instance, request, form)

            # post save field hooks
            for field in fields:
                field._plugin_instance.form_post_save(
                    instance=field._model_instance,
                    form=form,
                    request=request,
                )

            form_post_save.send(
                sender=models.FormPlugin,
                instance=instance,
                form=form,
                request=request,
            )
        elif request.POST.get('form_plugin_id') == str(instance.id) and request.method == 'POST':
            # only call form_invalid if request is POST and form is not valid
            self.form_invalid(instance, request, form)

        return form

    def get_form_class(self, instance):
        """
        Constructs form class basing on children plugin instances.
        """
        fields = self.get_form_fields(instance)
        formClass = (
            type(FormSubmissionBaseForm)
            ('AldrynDynamicForm', (FormSubmissionBaseForm,), fields)
        )
        return formClass

    def get_form_fields(self, instance: models.FormPlugin) -> Dict:
        form_fields = {}
        fields = instance.get_form_fields()

        for field in fields:
            plugin_instance = field.plugin_instance                     # aldryn_forms.models.FieldPlugin
            field_plugin = plugin_instance.get_plugin_class_instance()  # aldryn_forms.cms_plugins.TextField
            form_fields[field.name] = field_plugin.get_form_field(plugin_instance)
            form_fields[field.name]._cms_form_plugin = self
        return form_fields

    def get_form_kwargs(self, instance, request):
        kwargs = {
            'form_plugin': instance,
            'request': request,
        }

        if request.POST.get('form_plugin_id') == str(instance.id) and request.method in ('POST', 'PUT'):
            kwargs['data'] = request.POST.copy()
            kwargs['data']['language'] = instance.language
            kwargs['data']['form_plugin_id'] = instance.pk
            kwargs['files'] = request.FILES
        return kwargs

    def get_success_url(self, instance: models.FormPlugin, post_ident: Optional[str]) -> str:
        duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
        if duration and post_ident is not None and instance.success_url is not None:
            result = urlparse(instance.success_url)
            params = parse_qs(result.query)
            params[ALDRYN_FORMS_POST_IDENT_NAME] = post_ident
            result = result._replace(query=urlencode(params))
            return result.geturl()
        return instance.success_url

    def send_success_message(self, instance, request):
        """
        Sends a success message to the request user
        using django's contrib.messages app.
        """
        if instance.success_message:
            message = markdown.markdown(instance.success_message)
            if request.META.get('HTTP_X_REQUESTED_WITH') == "XMLHttpRequest":
                request.aldryn_forms_success_message = message
            else:
                messages.success(request, mark_safe(message))

    def save_new_submission(self, form: FormSubmissionBaseForm, post_ident: str) -> SubmittedToBeSent:
        """Save a new submission to be sent."""
        return SubmittedToBeSent.objects.create(
            name=form.instance.name,
            data=form.instance.data,
            recipients=form.instance.recipients,
            language=form.instance.language,
            form_url=form.instance.form_url,
            sent_at=form.instance.sent_at,
            post_ident=post_ident,
            honeypot_filled=form.instance.honeypot_filled
        )

    def postpone_send_notifications(
        self, instance: models.FormPlugin, form: FormSubmissionBaseForm
    ) -> List[Tuple[str, str]]:
        users = instance.recipients.exclude(email='')
        recipients = [user for user in users.iterator() if is_valid_recipient(user.email)]
        users_notified = [(get_user_name(user), user.email) for user in recipients]
        form.instance.set_recipients(users_notified)
        form.instance.set_form_data(form)

        post_ident = form.cleaned_data.get(ALDRYN_FORMS_POST_IDENT_NAME)
        if post_ident is None or post_ident.strip() == "":
            post_ident = form.generate_post_ident()
            form.initial_post_ident = post_ident
            form.cleaned_data[ALDRYN_FORMS_POST_IDENT_NAME] = post_ident
            new_instance = self.save_new_submission(form, post_ident)
            new_instance.webhooks.set(instance.webhooks.all())
        else:
            try:
                previous_submit = SubmittedToBeSent.objects.get(post_ident=post_ident)
                form.append_into_previous_submission(previous_submit)
            except SubmittedToBeSent.DoesNotExist:
                new_instance = self.save_new_submission(form, post_ident)
                new_instance.webhooks.set(instance.webhooks.all())

        return users_notified

    def send_notifications(self, instance, form):
        users = instance.recipients.exclude(email='')

        recipients = [user for user in users.iterator()
                      if is_valid_recipient(user.email)]

        context = {
            'form_name': instance.name,
            'form_data': form.get_serialized_form_fields(),
            'form_plugin': instance,
        }

        reply_to = []
        for name, value in form.cleaned_data.items():
            if name == EMAIL_REPLY_TO:
                reply_to.append(value)

        subject_template_base = getattr(settings, 'ALDRYN_FORMS_EMAIL_SUBJECT_TEMPLATES_BASE',
                                        getattr(settings, 'ALDRYN_FORMS_EMAIL_TEMPLATES_BASE', None))
        if subject_template_base:
            language = instance.language or get_language()
            subject_templates = get_template_names(language, subject_template_base, 'subject', 'txt')
        else:
            subject_templates = None

        try:
            send_mail(
                recipients=[user.email for user in recipients],
                context=context,
                template_base=getattr(
                    settings, 'ALDRYN_FORMS_EMAIL_TEMPLATES_BASE', 'aldryn_forms/emails/notification'),
                subject_templates=subject_templates,
                language=instance.language,
                reply_to=reply_to,
            )
        except smtplib.SMTPException as err:
            logger.error(err)

        users_notified = [
            (get_user_name(user), user.email) for user in recipients]
        return users_notified


class FormWithIdentPlugin(FormPlugin):
    render_template = True
    name = _("Form with Ident field")
    ident_field_name = ALDRYN_FORMS_POST_IDENT_NAME


class Fieldset(FieldContainer):
    render_template = True
    name = _('Fieldset')
    model = models.FieldsetPlugin

    fieldsets = (
        (None, {
            'fields': (
                'legend',
            )
        }),
        (_('Advanced Settings'), {
            'classes': ('collapse',),
            'fields': (
                'custom_classes',
            )
        }),
    )

    def get_render_template(self, context, instance, placeholder):
        try:
            form_plugin = context['form'].form_plugin
        except KeyError:
            # technically a fieldset is not allowed outside a form.
            # unfortunately, there's no builtin way to enforce this on the cms
            form_plugin = None
        templates = self.get_template_names(instance, form_plugin)
        return select_template(templates)

    def get_template_names(self, instance, form_plugin=None):
        template_names = ['aldryn_forms/fieldset.html']

        if form_plugin:
            template = f'aldryn_forms/{form_plugin.plugin_type.lower()}/fieldset.html'
            template_names.insert(0, template)
        return template_names


class Field(FormElement):
    module = _('Form fields')
    # template name is calculated based on field
    render_template = True
    model = models.FieldPlugin

    # Custom field related attributes
    form_field = None
    form_field_widget = None
    form_field_enabled_options = [
        'label',
        'name',
        'help_text',
        'required',
        'attributes',
    ]
    form_field_disabled_options = []

    # Used to configure default fieldset in admin form
    fieldset_general_fields = [
        'label',
        'name',
        'placeholder_text',
        'required',
    ]
    fieldset_advanced_fields = [
        'attributes',
        'help_text',
        ('min_value', 'max_value',),
        'required_message',
        'custom_classes',
    ]

    def serialize_value(self, instance, value, is_confirmation=False):
        if isinstance(value, query.QuerySet):
            value = ', '.join(map(str, value))
        elif value is None:
            value = '-'
        return str(value)

    def serialize_field(self, form, field, is_confirmation=False):
        """Returns a (key, label, value) named tuple for the given field."""
        value = self.serialize_value(
            instance=field.plugin_instance,
            value=form.cleaned_data[field.name],
            is_confirmation=is_confirmation,
        )
        serialized_field = SerializedFormField(
            name=field.name,
            label=field.label,
            field_occurrence=field.field_occurrence,
            value=value,
        )
        return serialized_field

    def get_form_field(self, instance: FieldPluginBase) -> forms.Field:
        form_field_class = self.get_form_field_class(instance)
        form_field_kwargs = self.get_form_field_kwargs(instance)
        field = form_field_class(**form_field_kwargs)
        field.required = instance.required
        # allow fields access to their model plugin class instance
        field._model_instance = instance
        # and also to the plugin class instance
        field._plugin_instance = self
        field._cms_form_plugin = None
        return field

    def get_form_field_class(self, instance):
        return self.form_field

    def get_form_field_kwargs(self, instance):
        allowed_options = self.get_field_enabled_options()

        kwargs = {'widget': self.get_form_field_widget(instance)}

        if 'error_messages' in allowed_options:
            kwargs['error_messages'] = self.get_error_messages(instance=instance)
        if 'label' in allowed_options:
            kwargs['label'] = instance.label
        if 'help_text' in allowed_options:
            kwargs['help_text'] = instance.help_text
        if 'max_length' in allowed_options:
            kwargs['max_length'] = instance.max_value
        if 'required' in allowed_options:
            kwargs['required'] = instance.required
        if 'validators' in allowed_options:
            kwargs['validators'] = self.get_form_field_validators(instance)
        if 'initial_value' in allowed_options:
            kwargs['initial'] = instance.initial_value
        return kwargs

    def get_form_field_widget(self, instance):
        form_field_widget_class = self.get_form_field_widget_class(instance)
        form_field_widget_kwargs = self.get_form_field_widget_kwargs(instance)
        form_field_widget_kwargs['attrs'] = self.get_form_field_widget_attrs(instance)
        return form_field_widget_class(**form_field_widget_kwargs)

    def get_form_field_widget_class(self, instance):
        return self.form_field_widget

    def get_form_field_widget_attrs(self, instance):
        attrs = {}
        if instance.placeholder_text:
            attrs['placeholder'] = instance.placeholder_text
        if instance.custom_classes:
            attrs['class'] = instance.custom_classes
        if instance.attributes:
            attrs.update(instance.attributes)
        return attrs

    def get_form_field_widget_kwargs(self, instance):
        return {}

    def render(self, context: PluginContext, instance: models.FieldPlugin, placeholder: str) -> PluginContext:
        context = super().render(context, instance, placeholder)

        form = context.get('form')

        if form and hasattr(form, 'form_plugin'):
            form_plugin = form.form_plugin
            field_name = form_plugin.get_form_field_name(field=instance)
            if not form[field_name].is_hidden:
                # Do not render hidden fields because they are rendered in template aldryn_forms/form.html
                # in section {% for field in form.hidden_fields %}
                context['field'] = form[field_name]
        return context

    def get_render_template(self, context, instance, placeholder):
        try:
            form_plugin = context['form'].form_plugin
        except KeyError:
            # technically a field is not allowed outside a form.
            # unfortunately, there's no builtin way to enforce this on the cms
            form_plugin = None
        templates = self.get_template_names(instance, form_plugin)
        return select_template(templates)

    def get_fieldsets(self, request, obj=None):
        if self.fieldsets or self.fields:
            # Allows overriding using fieldsets or fields. If you do that none
            # of the automatic stuff kicks in and you have to take care of
            # declaring all fields you want on the form!
            # This ends up having the same behaviour as declared_fieldsets in
            # Django <1.9 had.
            return super().get_fieldsets(request, obj=obj)

        fieldsets = [
            (None, {'fields': list(self.fieldset_general_fields)}),
        ]

        if self.fieldset_advanced_fields:
            fieldsets.append(
                (
                    _('Advanced Settings'), {
                        'classes': ('collapse',),
                        'fields': list(self.fieldset_advanced_fields),
                    }
                ))
        return fieldsets

    def get_error_messages(self, instance):
        if instance.required_message:
            return {'required': instance.required_message}
        else:
            return {}

    def get_form_field_validators(self, instance):
        return []

    def get_field_enabled_options(self):
        enabled_options = self.form_field_enabled_options
        disabled_options = self.form_field_disabled_options
        return [option for option in enabled_options if option not in disabled_options]

    def get_template_names(self, instance, form_plugin=None):
        template_names = [
            f'aldryn_forms/fields/{instance.field_type}.html',
            'aldryn_forms/field.html',
        ]

        if form_plugin:
            template = 'aldryn_forms/{}/fields/{}.html'.format(
                form_plugin.plugin_type.lower(),
                instance.field_type,
            )
            template_names.insert(0, template)
        return template_names

    # hooks to allow processing of form data per field
    def form_pre_save(self, instance, form, **kwargs):
        pass

    def form_post_save(self, instance, form, **kwargs):
        pass


class BaseTextField(Field):
    form = TextFieldForm
    form_field = forms.CharField
    form_field_widget = forms.CharField.widget
    form_field_widget_input_type = 'text'
    form_field_enabled_options = [
        'label',
        'name',
        'help_text',
        'required',
        'max_length',
        'error_messages',
        'validators',
        'placeholder',
        'initial_value',
    ]

    def get_form_field_validators(self, instance):
        validators = []

        if instance.min_value:
            validators.append(MinLengthValidator(instance.min_value))
        return validators

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)
        attrs['type'] = self.form_field_widget_input_type
        return attrs


class TextField(BaseTextField):
    name = _('Text Field')


class HoneypotCharField(forms.CharField):

    def clean(self, value):
        cleaned_value = super().clean(value)
        if cleaned_value:
            logger.info(f'Post disabled due to Honeypot "{self.label}" value: "{value}"')
            self._cms_form_plugin.honeypot_filled = True
        return cleaned_value


class HoneypotField(BaseTextField):
    name = _('Honeypot Field')
    form = forms.ModelForm
    form_field = HoneypotCharField
    form_field_widget = HoneypotCharField.widget
    form_field_enabled_options = [
        'label',
        'name',
        'help_text',
        'validators',
        'placeholder',
        'initial_value',
    ]
    fieldset_general_fields = [
        'label',
        'name',
        'placeholder_text',
    ]
    fieldset_advanced_fields = [
        'attributes',
        'help_text',
        'custom_classes',
    ]


class TextAreaField(BaseTextField):
    name = _('Text Area Field')
    model = models.TextAreaFieldPlugin
    form = TextAreaFieldForm
    form_field_widget = forms.Textarea
    fieldset_general_fields = [
        'label',
        'name',
        'placeholder_text',
        ('text_area_rows', 'text_area_columns',),
        'required',
    ]
    fieldset_advanced_fields = [
        'help_text',
        ('min_value', 'max_value',),
        'required_message',
        'custom_classes',
    ]

    def get_form_field_widget(self, instance):
        widget = super().get_form_field_widget(instance)

        # django adds the cols and rows attributes by default.
        # remove them if the user did not specify a value for them.
        if not instance.text_area_columns:
            del widget.attrs['cols']

        if not instance.text_area_rows:
            del widget.attrs['rows']
        return widget

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)

        if instance.text_area_columns:
            attrs['cols'] = instance.text_area_columns
        if instance.text_area_rows:
            attrs['rows'] = instance.text_area_rows
        return attrs


class HiddenField(BaseTextField):
    name = _('Hidden Field')
    form = HiddenFieldForm
    form_field_widget_input_type = 'hidden'
    fieldset_general_fields = ['name', 'initial_value']
    fieldset_advanced_fields = []


class PhoneField(BaseTextField):
    name = _('Phone Field')
    form_field_widget_input_type = 'phone'


class DateField(BaseTextField):
    name = _('Date Field')
    model = models.DateFieldPlugin
    form = DateFieldForm
    form_field_widget_input_type = 'date'
    fieldset_general_fields = [
        'label',
        'name',
        'required',
    ]
    fieldset_advanced_fields = [
        ('earliest_date', 'latest_date', 'input_step'),
        'attributes',
        'help_text',
        'required_message',
        'custom_classes',
    ]

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)
        if instance.earliest_date is not None:
            attrs['min'] = instance.earliest_date.isoformat()
        if instance.latest_date is not None:
            attrs['max'] = instance.latest_date.isoformat()
        if instance.input_step is not None:
            attrs['step'] = instance.input_step
        return attrs


class DateTimeLocalField(BaseTextField):
    name = _('Datetime local Field')
    model = models.DateTimeLocalFieldPlugin
    form = DateTimeFieldForm
    form_field_widget_input_type = 'datetime-local'
    fieldset_general_fields = [
        'label',
        'name',
        'required',
    ]
    fieldset_advanced_fields = [
        ('earliest_datetime', 'latest_datetime', 'input_step'),
        'attributes',
        'help_text',
        'required_message',
        'custom_classes',
    ]

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)
        if instance.earliest_datetime is not None:
            attrs['min'] = instance.earliest_datetime.replace(tzinfo=None).isoformat(timespec='minutes')
        if instance.latest_datetime is not None:
            attrs['max'] = instance.latest_datetime.replace(tzinfo=None).isoformat(timespec='minutes')
        if instance.input_step is not None:
            attrs['step'] = instance.input_step
        return attrs


class TimeField(BaseTextField):
    name = _('Time Field')
    model = models.TimeFieldPlugin
    form = TimeFieldForm
    form_field_widget_input_type = 'time'
    fieldset_advanced_fields = [
        ('earliest_time', 'latest_time', 'input_step'),
        'data_list',
        'readonly',
        'attributes',
        'help_text',
        'required_message',
        'custom_classes',
    ]

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)
        if instance.earliest_time is not None:
            attrs['min'] = instance.earliest_time.isoformat(timespec='minutes')
        if instance.latest_time is not None:
            attrs['max'] = instance.latest_time.isoformat(timespec='minutes')
        if instance.input_step is not None:
            attrs['step'] = instance.input_step
        if instance.data_list is not None:
            attrs['list'] = instance.data_list
        if instance.readonly:
            attrs['readonly'] = True
        return attrs


class NumberField(BaseTextField):
    name = _('Number Field')
    form_field_widget_input_type = 'number'


class EmailField(BaseTextField):
    name = _('Email Field')
    model = models.EmailFieldPlugin
    form = EmailFieldForm
    form_field = forms.EmailField
    form_field_widget = forms.EmailInput
    form_field_widget_input_type = 'email'
    fieldset_advanced_fields = [
        'email_send_notification',
        'email_subject',
        'email_body',
    ] + Field.fieldset_advanced_fields
    email_template_base = 'aldryn_forms/emails/user/notification'

    def send_notification_email(self, email, form, form_field_instance):
        context = {
            'form_name': form.instance.name,
            'form_data': form.get_serialized_form_fields(is_confirmation=True),
            'body_text': form_field_instance.email_body,
        }
        try:
            send_mail(
                recipients=[email],
                context=context,
                subject=form_field_instance.email_subject,
                template_base=self.email_template_base
            )
        except smtplib.SMTPException as err:
            logger.error(err)

    def form_post_save(self, instance: models.EmailFieldPlugin, form: forms.Form, **kwargs):
        # form: <class 'django.forms.widgets.AldrynDynamicForm'>
        # form.instance: <class 'aldryn_forms.models.FormSubmission'>
        if form.instance.honeypot_filled:
            return
        field_name = form.form_plugin.get_form_field_name(field=instance)

        email = form.cleaned_data.get(field_name)

        if email and instance.email_send_notification:
            self.send_notification_email(email, form, instance)


class FileField(Field):
    name = _('File upload field')
    model = models.FileUploadFieldPlugin

    form = FileFieldForm
    form_field = RestrictedFileField
    form_field_widget = RestrictedFileField.widget
    form_field_enabled_options = [
        'label',
        'help_text',
        'required',
        'error_messages',
        'validators',
    ]
    fieldset_general_fields = [
        'upload_to',
    ] + Field.fieldset_general_fields
    fieldset_advanced_fields = [
        'help_text',
        'max_size',
        'accepted_types',
        'required_message',
        'custom_classes',
        'enable_js',
    ]

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)
        if hasattr(instance, 'accepted_types') and instance.accepted_types:
            attrs['accept'] = ",".join(re.split(r"\s+", instance.accepted_types))
        if instance.max_size:
            attrs['data-max_size'] = instance.max_size
        if instance.enable_js:
            attrs['data-enable_js'] = "on"
        return attrs

    def get_form_field_kwargs(self, instance):
        kwargs = super().get_form_field_kwargs(instance)
        if instance.max_size:
            if 'help_text' in kwargs:
                kwargs['help_text'] = kwargs['help_text'].replace(
                    'MAXSIZE', filesizeformat(instance.max_size))
            kwargs['max_size'] = instance.max_size
        if hasattr(instance, 'accepted_types') and instance.accepted_types:
            kwargs['accepted_types'] = re.split(r"\s+", instance.accepted_types)
        return kwargs

    def serialize_value(self, instance, value, is_confirmation=False):
        links = []
        for item in value:
            if item:
                links.append(item.original_filename if is_confirmation else item.absolute_uri)
        return "\n".join(links)

    def form_pre_save(self, instance, form, **kwargs):
        """Save the uploaded file to django-filer

        The type of model (file or image) is automatically chosen by trying to
        open the uploaded file.
        """
        request = kwargs['request']

        filer_file_instances = []
        field_name = form.form_plugin.get_form_field_name(field=instance)

        for uploaded_file in request.FILES.getlist(field_name):
            if uploaded_file.content_type == 'image/svg+xml':
                model = imagemodels.Image
            else:
                try:
                    with Image.open(uploaded_file) as img:
                        img.verify()
                except:  # noqa
                    model = filemodels.File
                else:
                    model = imagemodels.Image

            filer_file = model(
                folder=instance.upload_to,
                file=uploaded_file,
                name=uploaded_file.name,
                original_filename=uploaded_file.name,
                is_public=True,
            )
            filer_file.save()

            # NOTE: This is a hack to make the full URL available later when we
            # need to serialize this field. We avoid to serialize it here directly
            # as we could still need access to the original filer File instance.
            filer_file.absolute_uri = request.build_absolute_uri(filer_file.url)
            filer_file_instances.append(filer_file)

        form.cleaned_data[field_name] = filer_file_instances


class MultipleFilesField(FileField):

    name = _('Multiple files upload field')
    model = models.MultipleFilesUploadFieldPlugin
    form_field = RestrictedMultipleFilesField
    form_field_widget = RestrictedMultipleFilesField.widget
    fieldset_advanced_fields = [
        'help_text',
        'max_size',
        'max_files',
        'accepted_types',
        'required_message',
        'custom_classes',
        'enable_js',
    ]

    def get_form_field_widget_attrs(self, instance):
        attrs = super().get_form_field_widget_attrs(instance)
        attrs['multiple'] = True
        if instance.max_files:
            attrs['data-max_files'] = instance.max_files
        return attrs

    def get_form_field_kwargs(self, instance):
        kwargs = super().get_form_field_kwargs(instance)
        if instance.max_files:
            kwargs['max_files'] = instance.max_files
        return kwargs


class ImageField(FileField):
    name = _('Image upload field')
    model = models.ImageUploadFieldPlugin

    form = ImageFieldForm
    form_field = RestrictedImageField
    form_field_widget = RestrictedImageField.widget
    fieldset_general_fields = [
        'upload_to',
    ] + Field.fieldset_general_fields
    fieldset_advanced_fields = [
        'help_text',
        'max_size',
        ('max_width', 'max_height',),
        'required_message',
        'custom_classes',
    ]

    def get_form_field_kwargs(self, instance):
        kwargs = super().get_form_field_kwargs(instance)

        if instance.max_width:
            if 'help_text' in kwargs:
                kwargs['help_text'] = kwargs['help_text'].replace(
                    'MAXWIDTH', str(instance.max_width))
            kwargs['max_width'] = instance.max_width

        if instance.max_height:
            if 'help_text' in kwargs:
                kwargs['help_text'] = kwargs['help_text'].replace(
                    'MAXHEIGHT', str(instance.max_height))
            kwargs['max_height'] = instance.max_height

        return kwargs


class BooleanField(Field):
    # checkbox field
    # I add the above because searching for "checkbox" should give me this plugin :)
    name = _('Yes/No Field')

    form = BooleanFieldForm
    form_field = forms.BooleanField
    form_field_widget = form_field.widget
    form_field_enabled_options = [
        'label',
        'name',
        'attributes',
        'help_text',
        'required',
        'error_messages',
    ]
    fieldset_general_fields = [
        'label', 'name', 'required',
    ]
    fieldset_advanced_fields = [
        'attributes',
        'help_text',
        'required_message',
        'custom_classes',
    ]

    def serialize_value(self, instance, value, is_confirmation=False):
        return gettext('Yes') if value else gettext('No')


class SelectOptionInline(TabularInline):
    model = models.Option


class SelectField(Field):
    name = _('Select Field')

    form = SelectFieldForm
    form_field = forms.ModelChoiceField
    form_field_widget = form_field.widget
    form_field_enabled_options = [
        'label',
        'name',
        'attributes',
        'help_text',
        'required',
        'error_messages',
    ]
    fieldset_general_fields = [
        'label', 'name', 'required',
    ]
    fieldset_advanced_fields = [
        'attributes',
        'help_text',
        'required_message',
        'custom_classes',
    ]

    inlines = [SelectOptionInline]

    def get_form_field_kwargs(self, instance):
        kwargs = super().get_form_field_kwargs(instance)
        kwargs['queryset'] = instance.option_set.all()
        for opt in kwargs['queryset']:
            if opt.default_value:
                kwargs['initial'] = opt.pk
                break
        return kwargs


class MultipleSelectField(SelectField):
    name = _('Multiple Select Field')

    form = MultipleSelectFieldForm
    form_field = forms.ModelMultipleChoiceField
    form_field_widget = forms.CheckboxSelectMultiple
    form_field_enabled_options = [
        'label',
        'name',
        'attributes',
        'help_text',
        'required',
        'validators',
    ]
    fieldset_general_fields = [
        'label', 'name', 'required',
    ]
    fieldset_advanced_fields = [
        'attributes',
        ('min_value', 'max_value'),
    ]

    def get_form_field_validators(self, instance):
        validators = []
        if instance.min_value:
            validators.append(MinChoicesValidator(limit_value=instance.min_value))
        if instance.max_value:
            validators.append(MaxChoicesValidator(limit_value=instance.max_value))
        return validators

    def get_form_field_kwargs(self, instance):
        kwargs = super().get_form_field_kwargs(instance)
        if hasattr(instance, 'min_value') and instance.min_value == 0:
            kwargs['required'] = False

        kwargs['initial'] = [o.pk for o in kwargs['queryset'] if o.default_value]
        return kwargs


class MultipleCheckboxSelectField(MultipleSelectField):
    name = _('Multiple Checkbox Field')


class RadioSelectField(Field):
    name = _('Radio Select Field')

    form = RadioFieldForm
    form_field = forms.ModelChoiceField
    form_field_widget = forms.RadioSelect
    form_field_enabled_options = [
        'label',
        'name',
        'attributes',
        'help_text',
        'required',
        'error_messages',
    ]
    fieldset_general_fields = [
        'label', 'name', 'required',
    ]
    fieldset_advanced_fields = [
        'attributes',
        'help_text',
        'required_message',
        'custom_classes',
    ]

    inlines = [SelectOptionInline]

    def get_form_field_kwargs(self, instance):
        kwargs = super().get_form_field_kwargs(instance)
        kwargs['queryset'] = instance.option_set.all()
        kwargs['empty_label'] = None
        for opt in kwargs['queryset']:
            if opt.default_value:
                kwargs['initial'] = opt.pk
                break
        return kwargs


try:
    if not apps.is_installed("captcha"):  # django-simple-captcha
        raise ImportError('Module "captcha" is not in INSTALLED_APPS.')
    from captcha.fields import CaptchaField, CaptchaTextInput
except ImportError:
    pass
else:
    # Don't like doing this. But we shouldn't force captcha.
    class CaptchaField(Field):
        name = _('Captcha Field')
        form = CaptchaFieldForm
        form_field = CaptchaField
        form_field_widget = CaptchaTextInput
        form_field_enabled_options = ['label', 'error_messages']
        fieldset_general_fields = [
            'label',
        ]
        fieldset_advanced_fields = [
            'required_message',
        ]

        def serialize_field(self, *args, **kwargs):
            # None means don't serialize me
            return None

    plugin_pool.register_plugin(CaptchaField)


class SubmitButton(FormElement):
    render_template = 'aldryn_forms/submit_button.html'
    name = _('Submit Button')
    model = models.FormButtonPlugin


@plugin_pool.register_plugin
class HideContentWhenPostPlugin(CMSPluginBase):
    module = _('Forms')
    name = _("Hide content after submitting a form")
    model = CMSPlugin
    render_template = "aldryn_forms/hide_content_when_post.html"
    cache = False
    allow_children = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['display_content'] = context['request'].method != "POST"
        return context


plugin_pool.register_plugin(BooleanField)
plugin_pool.register_plugin(EmailField)
plugin_pool.register_plugin(FileField)
plugin_pool.register_plugin(MultipleFilesField)
plugin_pool.register_plugin(HiddenField)
plugin_pool.register_plugin(PhoneField)
plugin_pool.register_plugin(DateField)
plugin_pool.register_plugin(TimeField)
plugin_pool.register_plugin(DateTimeLocalField)
plugin_pool.register_plugin(NumberField)
plugin_pool.register_plugin(ImageField)
plugin_pool.register_plugin(Fieldset)
plugin_pool.register_plugin(FormPlugin)
plugin_pool.register_plugin(FormWithIdentPlugin)
plugin_pool.register_plugin(MultipleSelectField)
plugin_pool.register_plugin(MultipleCheckboxSelectField)
plugin_pool.register_plugin(RadioSelectField)
plugin_pool.register_plugin(SelectField)
plugin_pool.register_plugin(SubmitButton)
plugin_pool.register_plugin(TextAreaField)
plugin_pool.register_plugin(TextField)
plugin_pool.register_plugin(HoneypotField)
