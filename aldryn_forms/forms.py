import json
import re
from typing import Dict, List, Optional

from django import forms
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorDict
from django.forms.widgets import ClearableFileInput
from django.utils.crypto import get_random_string
from django.utils.module_loading import import_string
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from easy_thumbnails.VIL import Image as VILImage
from PIL import Image

from .constants import ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, ALDRYN_FORMS_POST_IDENT_NAME, MAX_IDENT_SIZE
from .models import FormPlugin, FormSubmission, FormSubmissionBase
from .sizefield.utils import filesizeformat
from .utils import action_backend_choices, add_form_error, get_action_backends, get_user_model


class FileSizeCheckMixin:

    def __init__(self, *args, **kwargs):
        self.files = []  # This is set in FormPlugin.process_form() in cms_plugins.py
        self.max_size = kwargs.pop('max_size', None)
        self.accepted_types = kwargs.pop('accepted_types', [])
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)

        if not self.files:
            return []

        all_errors = []

        # Check file extension.
        if self.accepted_types:
            accepted_types, main_mimetypes = self.split_mimetypes(self.accepted_types)
            errors = []
            for file_in_memory in self.files:
                match = re.search(r'(\.\w+)$', file_in_memory.name.lower())
                extension = match.group(1) if match else None  # '.csv'
                if not (
                    extension in self.accepted_types
                    or file_in_memory.content_type in self.accepted_types  # noqa: W503 line break before bin operator
                    or file_in_memory.content_type.split("/")[0] in main_mimetypes  # noqa: W503
                ):
                    errors.append(gettext('"%(file_name)s" is not of accepted file type.') % {
                        'file_name': file_in_memory.name})
            if errors:
                all_errors.append(
                    " ".join(errors) + " " + gettext("Accepted file types are") + ": " + ", ".join(
                        self.accepted_types) + ".")

        # Check files size summary.
        if self.max_size is not None:
            errors = []
            files_size_summary = 0
            for file_in_memory in self.files:
                files_size_summary += file_in_memory.size
            if files_size_summary > self.max_size:
                if len(self.files) > 1:
                    msg = gettext('The total file size has exceeded the specified limit %(size)s.')
                else:
                    msg = gettext('File size exceeded the specified limit %(size)s.')
                all_errors.append(msg % {'size': filesizeformat(self.max_size)})

        if all_errors:
            raise forms.ValidationError(" ".join(all_errors))
        return self.files

    def split_mimetypes(self, accepted_types):
        """Split mimetypes with wildcards."""
        # Example of accepted_types: ['.pdf', 'text/plain', 'application/msword', 'image/*', 'text/*']
        accepted, main_mimetypes = [], []
        for name in accepted_types:
            match = re.match(r'(\w+)/\*', name)
            if match:
                main_mimetypes.append(match.group(1))
            else:
                accepted.append(name)
        return accepted, main_mimetypes


class RestrictedFileField(FileSizeCheckMixin, forms.FileField):
    """Restricted File Field."""


class ClearableMultipleFileInput(ClearableFileInput):
    """Clearable Multiple File Input."""

    allow_multiple_selected = True


class RestrictedMultipleFilesField(FileSizeCheckMixin, forms.FileField):

    widget = ClearableMultipleFileInput

    def __init__(self, *args, **kwargs):
        self.max_files = kwargs.pop('max_files', None)
        super().__init__(*args, **kwargs)

    def _to_python_one_field(self, data):
        if data in self.empty_values:
            return None

        # UploadedFile objects should have name and size attributes.
        try:
            file_name = data.name
            file_size = data.size
        except AttributeError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        if self.max_length is not None and len(file_name) > self.max_length:
            params = {"max": self.max_length, "length": len(file_name)}
            raise ValidationError(
                self.error_messages["max_length"], code="max_length", params=params
            )
        if not file_name:
            raise ValidationError(self.error_messages["invalid"], code="invalid")
        if not self.allow_empty_file and not file_size:
            raise ValidationError(self.error_messages["empty"], code="empty")

        return data

    def to_python(self, data):
        py_data = []
        for item in data:
            py_data.append(self._to_python_one_field(item))
        return py_data

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if not self.files:
            return []
        if self.max_files is not None and len(self.files) > self.max_files:
            raise forms.ValidationError(
                gettext("The number of uploaded files exceeded the set limit of %(limit)s.") % {
                    'limit': self.max_files
                })
        return self.files


def validate_image_and_svg_file_extension(value):
    if value.content_type == 'image/svg+xml':
        return True
    return validators.validate_image_file_extension(value)


class RestrictedImageField(FileSizeCheckMixin, forms.ImageField):

    default_validators = [validate_image_and_svg_file_extension]

    def __init__(self, *args, **kwargs):
        self.max_width = kwargs.pop('max_width', None)
        self.max_height = kwargs.pop('max_height', None)
        super().__init__(*args, **kwargs)

    def to_python(self, data):
        """
        Check that the file-upload field data contains a valid image (GIF, JPG,
        PNG, etc. -- whatever Pillow supports).
        """
        # Skip calling parent class forms.ImageField.
        f = super(forms.FileField, self).to_python(data)
        if f is None:
            return None

        if data.content_type == 'image/svg+xml':
            image = VILImage.load(data)
            if image is None:
                raise ValidationError(self.error_messages['invalid_image'], code='invalid_image')
            f.image = image
            f.content_type = data.content_type
            return f
        return super().to_python(data)

    def _clean_image(self, data):
        if data is None or not any([self.max_width, self.max_height]):
            return data

        if hasattr(data, 'image'):
            # Django >= 1.8
            width, height = data.image.size
        else:
            width, height = Image.open(data).size
            # cleanup after ourselves
            data.seek(0)

        if self.max_width and width > self.max_width:
            raise forms.ValidationError(
                gettext(
                    'Image width must be under %(max_size)s pixels. '
                    'Current width is %(actual_size)s pixels.'
                ) % {
                    'max_size': self.max_width,
                    'actual_size': width,
                })

        if self.max_height and height > self.max_height:
            raise forms.ValidationError(
                gettext(
                    'Image height must be under %(max_size)s pixels. '
                    'Current height is %(actual_size)s pixels.'
                ) % {
                    'max_size': self.max_height,
                    'actual_size': height,
                })

        return data

    def clean(self, *args, **kwargs):
        data = super().clean(*args, **kwargs)
        new_data = []
        for item in data:
            new_data.append(self._clean_image(item))
        return new_data


class DummyChecker:
    # https://gitlab.nic.cz/websites/django-cms-qe/-/blob/master/cms_qe_auth/utils.py#L47

    def __init__(self, hostname: str):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    def check(self, address: str) -> None:
        pass


def get_email_availability_checker_class():
    """Get function to check email availability."""
    # https://gitlab.nic.cz/websites/django-cms-qe/-/blob/master/cms_qe/settings/base/auth.py#L14
    backend = import_string(settings.EMAIL_BACKEND)
    if hasattr(backend, "host"):
        # Check only smtp backend.
        try:
            location = settings.ALDRYN_FORMS_EMAIL_AVAILABILITY_CHECKER_CLASS
            return import_string(location)
        except (AttributeError, ImportError):
            pass
    return DummyChecker


class FormSubmissionBaseForm(forms.Form):

    # these fields are internal.
    # by default we ignore all hidden fields when saving form data to db.
    language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        widget=forms.HiddenInput()
    )
    form_plugin_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.form_plugin = kwargs.pop('form_plugin')
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        language = self.form_plugin.language
        self.email_availability_checker_class = get_email_availability_checker_class()
        self.initial_post_ident = None

        self.instance = FormSubmission(
            name=self.form_plugin.name,
            language=language,
            form_url=self.request.build_absolute_uri(self.request.path),
        )
        self.fields['language'].initial = language
        self.fields['form_plugin_id'].initial = self.form_plugin.pk

    def _add_error(self, message, field=NON_FIELD_ERRORS):
        try:
            self._errors[field].append(message)
        except (KeyError, TypeError):
            if not self._errors:
                self._errors = ErrorDict()
            self._errors[field] = self.error_class([message])

    def get_serialized_fields(self, is_confirmation=False):
        """
        The `is_confirmation` flag indicates if the data will be used in a
        confirmation email sent to the user submitting the form or if it will be
        used to render the data for the recipients/admin site.
        """
        for field in self.form_plugin.get_form_fields():
            plugin = field.plugin_instance.get_plugin_class_instance()
            # serialize_field can be None or SerializedFormField  namedtuple instance.
            # if None then it means we shouldn't serialize this field.
            serialized_field = plugin.serialize_field(self, field, is_confirmation)

            if serialized_field:
                yield serialized_field

    def get_serialized_field_choices(self, is_confirmation=False):
        """Renders the form data in a format suitable to be serialized.
        """
        fields = self.get_serialized_fields(is_confirmation)
        fields = [(field.label, field.value) for field in fields]
        return fields

    def get_cleaned_data(self, is_confirmation=False):
        fields = self.get_serialized_fields(is_confirmation)
        form_data = {field.name: field.value for field in fields}
        return form_data

    def clean(self):
        if self.errors:
            return self.cleaned_data
        with self.email_availability_checker_class(settings.EMAIL_HOST) as checker:
            for field in self.form_plugin.get_form_fields():
                plugin = field.plugin_instance.get_plugin_class_instance()
                if hasattr(plugin, "send_notification_email") and plugin.send_notification_email:
                    serialized_field = plugin.serialize_field(self, field)
                    if serialized_field.value:
                        try:
                            checker.check(serialized_field.value)
                        except ValidationError:
                            self._add_error(_("This email is unavailable."), serialized_field.name)
        return self.cleaned_data

    def generate_post_ident(self) -> str:
        """Generate new post_ident."""
        return self.initial_post_ident if self.initial_post_ident else get_random_string(MAX_IDENT_SIZE)

    def save_form_submission(self, post_ident: Optional[str]) -> None:
        """Save a new submission with unique ID."""
        self.instance.post_ident = post_ident
        self.instance.set_form_data(self)
        self.instance.save()

    def append_into_previous_submission(self, previous_submit: FormSubmissionBase) -> None:
        """Append post into previous submission."""
        data: List[Dict[str, str]] = json.loads(previous_submit.data)
        fields = self.get_serialized_fields(is_confirmation=False)
        fields_as_dicts = [field._asdict() for field in fields if field.name != ALDRYN_FORMS_POST_IDENT_NAME]
        data.extend(fields_as_dicts)
        previous_submit.data = json.dumps(data)
        if self.instance.honeypot_filled:
            previous_submit.honeypot_filled = True
        previous_submit.save()

    def save(self, commit=False) -> FormSubmissionBase:
        """Save a new submission or append into a previous one."""
        post_ident = self.cleaned_data.get(ALDRYN_FORMS_POST_IDENT_NAME)
        if post_ident is None:
            duration = getattr(settings, ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION, 0)
            post_ident = self.generate_post_ident() if duration else None
            self.save_form_submission(post_ident)
        else:
            try:
                previous_submit = FormSubmission.objects.get(post_ident=post_ident)
                self.append_into_previous_submission(previous_submit)
                return previous_submit
            except FormSubmission.DoesNotExist:
                self.save_form_submission(post_ident)
        return self.instance


class ExtandableErrorForm(forms.ModelForm):

    def append_to_errors(self, field, message):
        add_form_error(form=self, message=message, field=field)


class FormPluginForm(ExtandableErrorForm):
    action_backend = forms.ChoiceField(
        choices=action_backend_choices(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email_availability_checker_class = get_email_availability_checker_class()

        if getattr(settings, 'ALDRYN_FORMS_SHOW_ALL_RECIPIENTS', False) and 'recipients' in self.fields:
            self.fields['recipients'].queryset = get_user_model().objects.all()

    def clean_recipients(self):
        recipients = self.cleaned_data["recipients"]
        with self.email_availability_checker_class(settings.EMAIL_HOST) as checker:
            for user in recipients:
                if user.email:
                    checker.check(user.email)
        return recipients

    def clean(self):
        redirect_type = self.cleaned_data.get('redirect_type')
        redirect_page = self.cleaned_data.get('redirect_page')
        url = self.cleaned_data.get('url')

        if redirect_type:
            if redirect_type == FormPlugin.REDIRECT_TO_PAGE:
                if not redirect_page:
                    self.append_to_errors('redirect_page', _('Please provide CMS page for redirect.'))
                self.cleaned_data['url'] = None

            if redirect_type == FormPlugin.REDIRECT_TO_URL:
                if not url:
                    self.append_to_errors('url', _('Please provide an absolute URL for redirect.'))
                self.cleaned_data['redirect_page'] = None
        else:
            self.cleaned_data['url'] = None
            self.cleaned_data['redirect_page'] = None

        action_backend = get_action_backends().get(self.cleaned_data.get('action_backend'))
        if action_backend is not None:
            error = getattr(action_backend, "clean_form", lambda form: None)(self)
            if error:
                self.append_to_errors('action_backend', error)
        return self.cleaned_data


class BooleanFieldForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        if 'instance' not in kwargs:  # creating new one
            initial = kwargs.pop('initial', {})
            initial['required'] = False
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message', 'custom_classes']


class SelectFieldForm(forms.ModelForm):

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message', 'custom_classes']


class RadioFieldForm(forms.ModelForm):

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message', 'custom_classes']


class CaptchaFieldForm(forms.ModelForm):

    class Meta:
        # captcha is always required
        fields = ['label', 'help_text', 'required_message']


class MinMaxValueForm(ExtandableErrorForm):

    def clean(self):
        min_value = self.cleaned_data.get('min_value')
        max_value = self.cleaned_data.get('max_value')
        if min_value and max_value and min_value > max_value:
            self.append_to_errors('min_value', _('Min value can not be greater than max value.'))
        if self.cleaned_data.get('required') and min_value is not None and min_value < 1:
            self.append_to_errors(
                'min_value', _('If checkbox "Field is required" is set, "Min choices" must be at least 1.'))
        return self.cleaned_data


class TextFieldForm(MinMaxValueForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['min_value'].label = _('Min length')
        self.fields['min_value'].help_text = _('Required number of characters to type.')

        self.fields['max_value'].label = _('Max length')
        self.fields['max_value'].help_text = _('Maximum number of characters to type.')
        self.fields['max_value'].required = False

    class Meta:
        fields = ['label', 'placeholder_text', 'help_text',
                  'min_value', 'max_value', 'required', 'required_message', 'custom_classes']


class HiddenFieldForm(ExtandableErrorForm):
    class Meta:
        fields = ['name', 'initial_value']


class NoRequiredFieldsModelForm(forms.ModelForm):
    """No required fields ModelForm."""

    no_required_fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.no_required_fields:
            self.fields[name].required = False


class DateFieldForm(NoRequiredFieldsModelForm):
    """Date Field Form."""

    no_required_fields = ['earliest_date', 'latest_date']


class DateTimeFieldForm(NoRequiredFieldsModelForm):
    """Datetime Field Form."""

    no_required_fields = ['earliest_datetime', 'latest_datetime']


class TimeFieldForm(NoRequiredFieldsModelForm):
    """Datetime Field Form."""

    no_required_fields = ['earliest_time', 'latest_time']


class EmailFieldForm(TextFieldForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['min_value'].required = False
        self.fields['max_value'].required = False

    class Meta:
        fields = [
            'label',
            'placeholder_text',
            'help_text',
            'min_value',
            'max_value',
            'required',
            'required_message',
            'email_send_notification',
            'email_subject',
            'email_body',
            'custom_classes',
        ]

    def clean(self):
        if "name" in self.changed_data:
            _, action_backend = self.instance.get_parent_form_action_backend()
            if action_backend is not None:
                error = getattr(action_backend, "clean_field", lambda form: None)(self)
                if error:
                    self.append_to_errors('name', error)
        return super().clean()


class FileFieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['help_text'].help_text = _(
            'Explanatory text displayed next to input field. Just like this '
            'one. You can use MAXSIZE as a placeholder for the maximum size '
            'configured below.')

    class Meta:
        fields = ['label', 'help_text', 'required', 'required_message',
                  'custom_classes', 'upload_to', 'max_size']


class ImageFieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['help_text'].help_text = _(
            'Explanatory text displayed next to input field. Just like this '
            'one. You can use MAXSIZE, MAXWIDTH, MAXHEIGHT as a placeholders '
            'for the maximum file size and dimensions configured below.')

    class Meta:
        fields = FileFieldForm.Meta.fields + ['max_height', 'max_width']


class TextAreaFieldForm(TextFieldForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['max_value'].required = False

    class Meta:
        fields = ['label', 'placeholder_text', 'help_text', 'text_area_columns',
                  'text_area_rows', 'min_value', 'max_value', 'required', 'required_message', 'custom_classes']


class MultipleSelectFieldForm(MinMaxValueForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['min_value'].label = _('Min choices')
        self.fields['min_value'].help_text = _('Required amount of elements to chose.')

        self.fields['max_value'].label = _('Max choices')
        self.fields['max_value'].help_text = _('Maximum amount of elements to chose.')

    class Meta:
        # 'required' and 'required_message' depend on min_value field validator
        fields = ['label', 'help_text', 'min_value', 'max_value', 'custom_classes']
