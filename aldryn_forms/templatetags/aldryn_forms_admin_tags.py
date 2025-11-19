import os
import re
from urllib.parse import unquote, urlparse, urlunparse

from django import template
from django.conf import settings
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
    site = Site.objects.values_list('domain', flat=True).first()
    for word in re.split(r"(\s+)", value):
        if re.match(link_pattern, word):
            word = make_link(word, site)
        else:
            word = escape(word)
        content.append(word)

    return mark_safe("".join(content))


@register.filter
def display_field_value(field: SerializedFormField) -> str:
    if field.plugin_type in ("FileField", "ImageField", "MultipleFilesField"):
        site = Site.objects.values_list('domain', flat=True).first()
        links = [make_link(link, site) for link in re.split(r"\s+", field.value)]
        return mark_safe("\n".join(links))
    return media_filer_public_link(field.value)


def make_link(value: str, site: str) -> str:
    """Make link for the site."""
    result = urlparse(value)
    scheme = getattr(settings, "ALDRYN_FORMS_URL_SCHEME", result.scheme)
    url = urlunparse((scheme, site, result.path, result.params, result.query, result.fragment))
    filename = os.path.basename(unquote(result.path))
    return f"""<a href="{url}" title="{escape(value)}" target="_blank">{escape(filename)}</a>"""
