"""
The AldrynFormsPageField class, unlike the PageField class, also displays unpublished pages.
"""
from django.forms.widgets import Select

from cms.forms.fields import PageSelectFormField
from cms.forms.widgets import PageSelectWidget
from cms.models.fields import PageField

from djangocms_link.fields import LinkField, LinkFormField

from .cms_forms_utils import get_page_choices, get_site_choices
from .widgets import LinkWidget


class AldrynFormsPageSelectWidget(PageSelectWidget):

    def _build_widgets(self):
        site_choices = get_site_choices()
        page_choices = get_page_choices()
        self.site_choices = site_choices
        self.choices = page_choices
        self.widgets = (
            Select(choices=site_choices),
            Select(choices=[('', '----')]),
            Select(choices=self.choices, attrs={'style': "display:none;"}),
        )


class AldrynFormsAdminPageSelectField(PageSelectFormField):

    widget = AldrynFormsPageSelectWidget


class AldrynFormsPageField(PageField):

    default_form_class = AldrynFormsAdminPageSelectField


class AldrynLinkFormField(LinkFormField):

    widget = LinkWidget


class AldrynFormsLinkField(LinkField):

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", AldrynLinkFormField)
        return super().formfield(**kwargs)
