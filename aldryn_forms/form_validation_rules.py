from django.forms.fields import Field
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from captcha.fields import CaptchaField

from .cms_plugins import FormPlugin


CAPCHA_KEY = "aldryn_forms_captcha_is_required"


def captcha_required(request: HttpRequest, form: FormPlugin, name: str, value: str) -> list[str]:
    """Set captcha is required."""
    modified_fields = []
    if not request.session.get(CAPCHA_KEY):
        request.session[CAPCHA_KEY] = True
        for name, field in form.fields.items():
            if isinstance(field, CaptchaField):
                field.required = True
                for child in field.fields:
                    child.required = True
                for suffix in field.widget.widgets_names:
                    modified_fields.append(name + suffix)
                form._add_error(_("Fill in the captcha code."), name)
    return [{"required": modified_fields}]


def enable_captcha(request: HttpRequest, form: FormPlugin, form_fields: dict[str, Field], rule: dict[str, str]) -> None:
    """Enable captcha field in form."""
    if request.session.get(CAPCHA_KEY) and not (request.user.is_authenticated and request.toolbar.edit_mode_active):
        for field in form_fields.values():
            if isinstance(field, CaptchaField):
                field.required = True


def captcha_optional(request: HttpRequest, form: FormPlugin, rule: dict[str, str]) -> None:
    """Set captcha optional."""
    if CAPCHA_KEY in request.session:
        del request.session[CAPCHA_KEY]
