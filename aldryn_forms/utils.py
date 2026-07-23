import logging
import os
import re
import smtplib
from collections.abc import Sequence
from typing import TYPE_CHECKING, Dict, ItemsView, List, Optional
from urllib.parse import urlparse

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.forms.fields import Field
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.widgets import Textarea
from django.http import Http404, HttpRequest
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import Resolver404, resolve
from django.utils.module_loading import import_string
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from cms.models import CMSPlugin
from cms.plugin_pool import plugin_pool
from cms.utils.plugins import downcast_plugins

from emailit.api import send_mail
from emailit.utils import get_template_names


try:
    from constance import config as constance_config
except ModuleNotFoundError:
    constance_config = None


from .action_backends_base import BaseAction
from .compat import build_plugin_tree
from .constants import (
    ALDRYN_FORMS_ACTION_BACKEND_KEY_MAX_SIZE, ALDRYN_FORMS_POST_IDENT_NAME, DEFAULT_ALDRYN_FORMS_ACTION_BACKENDS,
    EMAIL_REPLY_TO,
)
from .validators import is_valid_recipient


if TYPE_CHECKING:  # pragma: no cover
    from .cms_plugins import FromPlugin
    from .models import FormPlugin, FormSubmissionBase, Recipient, SerializedFormField

logger = logging.getLogger(__name__)


def get_action_backends():
    base_error_msg = 'Invalid settings.ALDRYN_FORMS_ACTION_BACKENDS.'
    max_key_size = ALDRYN_FORMS_ACTION_BACKEND_KEY_MAX_SIZE

    try:
        backends = settings.ALDRYN_FORMS_ACTION_BACKENDS
    except AttributeError:
        backends = DEFAULT_ALDRYN_FORMS_ACTION_BACKENDS

    try:
        backends = {k: import_string(v) for k, v in backends.items()}
    except ImportError as e:
        raise ImproperlyConfigured(f'{base_error_msg} {e}')

    if any(len(key) > max_key_size for key in backends):
        raise ImproperlyConfigured(
            f'{base_error_msg} Ensure all keys are no longer than {max_key_size} characters.'
        )

    if not all(issubclass(klass, BaseAction) for klass in backends.values()):
        raise ImproperlyConfigured(
            '{} All classes must derive from aldryn_forms.action_backends_base.BaseAction'
            .format(base_error_msg)
        )

    if 'default' not in backends.keys():
        raise ImproperlyConfigured(f'{base_error_msg} Key "default" is missing.')

    try:
        [x() for x in backends.values()]  # check abstract base classes sanity
    except TypeError as e:
        raise ImproperlyConfigured(f'{base_error_msg} {e}')
    return backends


def action_backend_choices(*args, **kwargs):
    choices = tuple((key, klass.verbose_name) for key, klass in get_action_backends().items())
    return sorted(choices, key=lambda x: x[1])


def get_nested_plugins(parent_plugin, include_self=False):
    """
    Returns a flat list of plugins from parent_plugin. Replace AliasPlugin by descendants.
    """
    AliasPlugin = plugin_pool.get_plugin("Alias")

    found_plugins = []

    if include_self:
        found_plugins.append(parent_plugin)

    child_plugins = parent_plugin.get_children()

    for plugin in child_plugins:
        if issubclass(plugin.get_plugin_class(), AliasPlugin):
            if hasattr(plugin, "plugin"):
                found_plugins.extend(plugin.plugin.get_descendants())
            else:
                found_plugins.extend(plugin.get_descendants())
            bound_plugin = plugin.get_bound_plugin()
            if hasattr(bound_plugin, 'alias') and bound_plugin.alias:
                found_plugins.extend(bound_plugin.alias.get_plugins())
        else:
            found_plugins.extend(get_nested_plugins(plugin, include_self=True))

    return found_plugins


def get_plugin_tree(model, **kwargs):
    """
    Plugins in django CMS are highly related to a placeholder.

    This function builds a plugin tree for a plugin with no placeholder context.

    Makes as many database queries as many levels are in the tree.

    This is ok as forms shouldn't form very deep trees.
    """
    plugin = model.objects.get(**kwargs)
    plugin.parent = None
    current_level = [plugin]
    plugin_list = [plugin]
    while get_next_level(current_level).exists():
        current_level = get_next_level(current_level)
        current_level = downcast_plugins(current_level)
        plugin_list += current_level
    return build_plugin_tree(plugin_list)[0]


def get_next_level(current_level):
    all_plugins = CMSPlugin.objects.all()
    return all_plugins.filter(parent__in=[x.pk for x in current_level])


def add_form_error(form, message, field=NON_FIELD_ERRORS):
    try:
        form._errors[field].append(message)
    except KeyError:
        form._errors[field] = form.error_class([message])


def send_postponed_notifications(instance: "FormSubmissionBase") -> bool:
    """Send postponed notifications."""
    recipients = [user for user in instance.get_recipients() if is_valid_recipient(user.email)]
    if not recipients:
        return True
    form_data = instance.get_form_data()
    cleaned_data = [(field.name, field.value) for field in form_data]
    return send_email(recipients, instance, form_data, cleaned_data)


def send_email(
    recipients: List["Recipient"],
    instance: "FormSubmissionBase",
    form_data: List["SerializedFormField"],
    cleaned_data: ItemsView
) -> bool:
    """Send email."""
    context = {
        'form_name': instance.name,
        'form_data': form_data,
        'form_plugin': instance,
        'form_values': {sf.name: sf.value for sf in form_data},
    }
    subject_template_base = getattr(settings, 'ALDRYN_FORMS_EMAIL_SUBJECT_TEMPLATES_BASE',
                                    getattr(settings, 'ALDRYN_FORMS_EMAIL_TEMPLATES_BASE', None))
    if subject_template_base:
        language = instance.language or get_language()
        subject_templates = get_template_names(language, subject_template_base, 'subject', 'txt')
    else:
        subject_templates = None

    subject = None
    if constance_config is not None:
        template_string = getattr(constance_config, f"ALDRYN_FORMS_EMAIL_SUBJECT_{instance.language.upper()}", None)
        if template_string is not None:
            subject = Template(template_string).render(Context(context))

    reply_to = []
    for name, value in cleaned_data:
        if name == EMAIL_REPLY_TO:
            reply_to.append(value)

    append_attachments = getattr(settings, "ALDRYN_FORMS_APPEND_ATTACHMENTS", False)
    if constance_config is not None:
        append_attachments = getattr(constance_config, "ALDRYN_FORMS_APPEND_ATTACHMENTS", append_attachments)
    if append_attachments:
        attachments = prepare_attachments(get_upload_urls(form_data))
        if not attachments:
            attachments = None
    else:
        attachments = None

    try:
        send_mail(
            recipients=[user.email for user in recipients],
            context=context,
            template_base=getattr(
                settings, 'ALDRYN_FORMS_EMAIL_TEMPLATES_BASE', 'aldryn_forms/emails/notification'),
            subject=subject,
            subject_templates=subject_templates,
            language=instance.language,
            reply_to=reply_to,
            attachments=attachments,
        )
    except (smtplib.SMTPException, OSError) as err:
        logger.error(err)
        return False
    return True


def get_serialized_fields(form: forms.Form) -> Dict[str, str]:
    """Get serialized fields. Skip honeypost and ident field."""
    fields_as_dicts: List[Dict[str, str]] = []
    for field in form.get_serialized_fields(is_confirmation=False):
        item = field._asdict()
        if item["plugin_type"] == "HoneypotField" and not item["value"]:
            continue
        if field.name == ALDRYN_FORMS_POST_IDENT_NAME:
            continue
        fields_as_dicts.append(item)
    return fields_as_dicts


def get_upload_urls(form_data: List["SerializedFormField"]) -> set:
    """Get upload URLs."""
    urls = set()
    for field in form_data:
        if field.value and field.plugin_type in ("FileField", "ImageField", "MultipleFilesField"):
            urls.update(re.split(r"\s+", field.value))
    return urls


def prepare_attachments(urls: Sequence) -> list[tuple[str, bytes, str]]:
    """Prepare filename and content for email attachments."""
    attachments = []
    request = RequestFactory().request()
    request.user = get_user_model()(is_superuser=True)  # Necessary due to permissions.
    for url in urls:
        result = urlparse(url)
        try:
            match = resolve(result.path)
        except Resolver404 as err:
            logger.error(err)
            continue
        try:
            response = match.func(request=request, *match.args, **match.kwargs)
        except Http404 as err:
            logger.error(err)
            continue
        # https://github.com/divio/django-emailit/blob/0.2.4/emailit/api.py#L75
        # https://github.com/django/django/blob/5.2.8/django/core/mail/message.py#L309
        attachments.append((
            os.path.basename(result.path),  # filename
            response.getvalue(),  # content
            response.headers["Content-Type"]  # mimetype
        ))
    return attachments


def get_webhook_debug_url(key) -> Optional[str]:
    """Get webhook debug url."""
    return None if constance_config is None else getattr(constance_config, key, None)


def get_webhook_debug_admin_url() -> Optional[str]:
    """Get webhook debug admin url."""
    return get_webhook_debug_url("ALDRYN_FORMS_DEBUG_WEBHOOK_ADMIN_URL")


def get_webhook_debug_client_url() -> Optional[str]:
    """Get webhook debug url."""
    return get_webhook_debug_url("ALDRYN_FORMS_DEBUG_WEBHOOK_URL")


def get_form_anchor(pk: int) -> str:
    """Get form anchor."""
    return f"aldryn_form_{pk}"


def get_post_form(pk: int) -> str:
    """Get post form."""
    return f"post_aldryn_form_{pk}"


def compile_pattern(pattern):
    """Compile regular expression pattern."""
    if pattern is None:
        return None
    try:
        return re.compile(pattern)
    except re.error as error:
        logger.error(error)
    return None


def process_fnc(request: HttpRequest, fnc, *args) -> bool | list[str] | None:
    """Process function."""
    try:
        return import_string(fnc)(request, *args)
    except Exception as error:
        logging.error(error)
    return None


def process_error(request: HttpRequest, form, regex, name, value, rule, translations) -> bool | list[str] | None:
    """Process error."""
    if value is None:
        return None
    value = str(value)
    if not regex.match(value):
        return None
    fnc = rule.get("fnc")
    if fnc is not None:
        return process_fnc(request, fnc, form, name, value)
    else:
        error = rule.get("error", _("Invalid value"))
        language = translations.get(error, {})
        msg = language.get(request.LANGUAGE_CODE, error)
        form._add_error(msg, name)
    return None


def is_input_type(form, name, field_types) -> bool:
    """Check if field widget is required type."""
    if not field_types:
        return True
    if isinstance(form.fields[name].widget, Textarea):
        input_type = "textarea"
    else:
        input_type = getattr(form.fields[name].widget, "input_type", "text")
    return input_type in field_types


def form_rules_clean(request: HttpRequest, form: forms.Form, rules: dict) -> list[str]:
    """Form rules for form.clean."""
    clean_fields_again = []
    translations = rules.get("translations", {})
    for rule in rules.get("clean", []):
        if not isinstance(rule, dict):
            continue
        fields = rule.get("fields")
        if isinstance(fields, list):
            for name in fields:
                value = form.cleaned_data.get(name)
                if value is not None:
                    if regex := compile_pattern(rule.get("pattern")):
                        retval = process_error(request, form, regex, name, value, rule, translations)
                        if isinstance(retval, list):
                            clean_fields_again.extend(retval)
        elif isinstance(rule.get("fields_pattern"), dict):
            field_types = rule["fields_pattern"].get("types", [])
            field_name = rule["fields_pattern"].get("name")
            if not field_name:
                continue
            if regex_field := compile_pattern(field_name):
                if regex := compile_pattern(rule.get("pattern")):
                    for name, value in form.cleaned_data.items():
                        if regex_field.match(name) and is_input_type(form, name, field_types):
                            retval = process_error(request, form, regex, name, value, rule, translations)
                            if isinstance(retval, list):
                                clean_fields_again.extend(retval)
    return clean_fields_again


def form_rules_build_fields(
    request: HttpRequest, instance: "FormPlugin", form: "FromPlugin", form_fields: dict[str, Field], rules: dict
) -> None:
    """Form rules for plugin.get_form_fields."""
    for rule in rules.get("create", []):
        if "fnc" in rule:
            process_fnc(request, rule["fnc"], form, form_fields, rule)


def form_rules_is_valid(request: HttpRequest, form: forms.Form, rules: dict) -> None:
    """Form rules is_valid."""
    for rule in rules.get("success", []):
        if "fnc" in rule:
            process_fnc(request, rule["fnc"], form, rule)
