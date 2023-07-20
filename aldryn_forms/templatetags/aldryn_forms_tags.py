from django import template
from django.utils import encoding
from django.utils.safestring import mark_safe

import markdown as markdown_module


register = template.Library()


@register.simple_tag(takes_context=True)
def render_notification_text(context, email_notification, email_type):
    text_context = context.get('text_context')

    if not text_context or not email_notification:
        return

    render_func = 'render_%s' % email_type
    message = getattr(email_notification, render_func)(context=text_context)
    return mark_safe(message)


@register.simple_tag()
def render_form_widget(field, **kwargs):
    if "class" in kwargs and field.errors:
        if kwargs["class"]:
            kwargs["class"] += " "
        kwargs["class"] += "has-error"
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
