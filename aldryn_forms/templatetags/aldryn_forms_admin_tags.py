import re

from django import template
from django.contrib.sites.models import Site
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()

link_pattern = None


@register.filter
def media_filer_public_link(value):
    global link_pattern

    if not isinstance(value, str):
        return value

    if link_pattern is None:
        hostnames = "|".join(Site.objects.values_list('domain', flat=True))
        link_pattern = f"^https?://({hostnames})/media/filer_public/"

    content = []
    for word in re.split(r"(\s+)", value):
        if re.match(link_pattern, word):
            filename = escape(word.split("/")[-1])
            word = f"""<a href="{word}" target="_blank">{filename}</a>"""
        else:
            word = escape(word)
        content.append(word)

    return mark_safe("".join(content))
