import os
import re
from urllib.parse import unquote, urlparse

from django import template
from django.contrib.sites.models import Site
from django.utils.html import escape
from django.utils.safestring import mark_safe

from ..models import SerializedFormField


register = template.Library()

link_pattern = None


@register.filter
def media_filer_public_link(value: str) -> str:
    global link_pattern

    if not isinstance(value, str):
        return str(value)

    if link_pattern is None:
        hostnames = "|".join(Site.objects.values_list('domain', flat=True))
        link_pattern = f"^https?://({hostnames})/s?media/filer_(public|private)/"

    content = []
    for word in re.split(r"(\s+)", value):
        if re.match(link_pattern, word):
            filename = escape(word.split("/")[-1])
            word = f"""<a href="{word}" target="_blank">{filename}</a>"""
        else:
            word = escape(word)
        content.append(word)

    return mark_safe("".join(content))


@register.filter
def display_field_value(field: SerializedFormField) -> str:
    if field.plugin_type in ("FileField", "ImageField", "MultipleFilesField"):
        result = urlparse(field.value)
        filename = os.path.basename(unquote(result.path))
        return mark_safe(f"""<a href="{field.value}" target="_blank">{escape(filename)}</a>""")
    return media_filer_public_link(field.value)
