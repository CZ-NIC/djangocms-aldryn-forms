import logging
import smtplib
from typing import TYPE_CHECKING, NamedTuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.forms.forms import NON_FIELD_ERRORS
from django.utils.module_loading import import_string
from django.utils.translation import get_language

from cms.plugin_pool import plugin_pool
from cms.utils.moderator import get_cmsplugin_queryset
from cms.utils.plugins import downcast_plugins

from emailit.api import send_mail
from emailit.utils import get_template_names

from .action_backends_base import BaseAction
from .compat import build_plugin_tree
from .constants import ALDRYN_FORMS_ACTION_BACKEND_KEY_MAX_SIZE, DEFAULT_ALDRYN_FORMS_ACTION_BACKENDS
from .validators import is_valid_recipient


if TYPE_CHECKING:  # pragma: no cover
    from .models import FormSubmissionBase


class NameTypeField(NamedTuple):
    name: str
    value: str


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


def get_user_model():
    """
    Wrapper for get_user_model with compatibility for 1.5
    """
    # Notice these imports happen here to be compatible with django 1.7
    try:
        from django.contrib.auth import get_user_model as _get_user_model
    except ImportError:  # django < 1.5
        from django.contrib.auth.models import User
    else:
        User = _get_user_model()
    return User


def get_nested_plugins(parent_plugin, include_self=False):
    """
    Returns a flat list of plugins from parent_plugin. Replace AliasPlugin by descendants.
    """
    AliasPlugin = plugin_pool.get_plugin("AliasPlugin")
    found_plugins = []

    if include_self:
        found_plugins.append(parent_plugin)

    child_plugins = parent_plugin.get_children()

    for plugin in child_plugins:
        if issubclass(plugin.get_plugin_class(), AliasPlugin):
            if hasattr(plugin, "plugin"):
                found_plugins.extend(list(plugin.plugin.get_descendants().order_by('path')))
            else:
                found_plugins.extend(list(plugin.get_descendants().order_by('path')))
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
    all_plugins = get_cmsplugin_queryset()
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
    form_data = [NameTypeField(item.name, item.value) for item in instance.get_form_data()]
    context = {
        'form_name': instance.name,
        'form_data': form_data,
        'form_plugin': instance,
    }
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
        )
    except smtplib.SMTPException as err:
        logger.error(err)
        return False
    return True
