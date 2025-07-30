from django import template
from django.forms.boundfield import BoundField
from django.utils import encoding
from django.utils.safestring import mark_safe

import markdown as markdown_module

from aldryn_forms.models import FieldPluginBase


register = template.Library()


@register.simple_tag(takes_context=True)
def render_notification_text(context, email_notification, email_type):
    text_context = context.get('text_context')

    if not text_context or not email_notification:
        return

    render_func = 'render_%s' % email_type
    message = getattr(email_notification, render_func)(context=text_context)
    return mark_safe(message)


def _build_kwargs(field: BoundField, instance: FieldPluginBase) -> dict[str, str]:
    kwargs: dict[str, str] = {}
    if instance.custom_classes:
        kwargs["class"] = instance.custom_classes
    if "class" in kwargs and field.errors:
        if kwargs["class"]:
            kwargs["class"] += " "
        kwargs["class"] += "has-error"
    return kwargs


@register.simple_tag()
def render_form_widget(field: BoundField, instance: FieldPluginBase):
    markup = field.as_widget(attrs=_build_kwargs(field, instance))
    return mark_safe(markup)


@register.simple_tag()
def render_url_field(field: BoundField, instance: FieldPluginBase, **kwargs):
    kwargs = _build_kwargs(field, instance)
    if instance.list:
        kwargs["list"] = instance.get_html_id_list()
    if instance.min_value is not None:
        kwargs["minlength"] = instance.min_value
    for name in ("pattern", "readonly", "size", "spellcheck"):
        value = getattr(instance, name)
        if value:
            kwargs[name] = value
    markup = field.as_widget(attrs=kwargs)
    return mark_safe(markup)


@register.filter()
def force_text(val):
    return encoding.force_str(val)


@register.filter()
def force_text_list(val):
    return [encoding.force_str(v) for v in val]


@register.filter()
def markdown(text):
    return mark_safe(markdown_module.markdown(text))
