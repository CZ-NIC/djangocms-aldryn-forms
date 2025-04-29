"""
The AldrynFormsPageField class, unlike the PageField class, also displays unpublished pages.
"""
from djangocms_link.fields import LinkField, LinkFormField

from .widgets import LinkWidget


class AldrynLinkFormField(LinkFormField):

    widget = LinkWidget


class AldrynFormsLinkField(LinkField):

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", AldrynLinkFormField)
        return super().formfield(**kwargs)
