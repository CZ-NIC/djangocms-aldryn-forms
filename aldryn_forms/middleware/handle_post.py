# import markdown
from typing import Callable, Dict, Optional, Tuple, Union

from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _

from aldryn_forms.constants import ALDRYN_FORMS_POST_IDENT_NAME
from aldryn_forms.forms import FormSubmissionBaseForm
from aldryn_forms.models import FormPlugin
from aldryn_forms.utils import get_plugin_tree


class HandleHttpPost(MiddlewareMixin):
    """Handle HTTP POST."""

    def process_view(
        self, request: HttpRequest, callback: Callable, callback_args: Tuple[str, ...], callback_kwargs: Dict[str, str]
    ) -> Optional[Union[HttpResponseRedirect, JsonResponse]]:
        """Process view when request method is POST and when the form plugin is found."""

        if request.method != 'POST':
            return get_response(request, message=_("The method is not of type POST."))

        # The following code is written according to the function submit_form_view in views.py.
        form_plugin_id = request.POST.get('form_plugin_id')
        if form_plugin_id is None:
            return get_response(request, message=_("POST does not contain a form id."))
        if not form_plugin_id.isdigit():
            return get_response(request, message=_("Incorrect form id type."))

        try:
            form_plugin = get_plugin_tree(FormPlugin, pk=form_plugin_id)
        except FormPlugin.DoesNotExist:
            return get_response(request, message=_("The form is not active."))

        form_plugin_instance = form_plugin.get_plugin_instance()[1]
        form = form_plugin_instance.process_form(form_plugin, request)

        return get_response(request, form, form_plugin)


def get_response(
    request: HttpRequest,
    form: FormSubmissionBaseForm = None,
    form_plugin: FormPlugin = None,
    message: str = None
) -> Optional[Union[HttpResponseRedirect, JsonResponse]]:
    """Get response type."""
    if request.method == 'POST':
        data = {"status": "ERROR"}
        if form is None:
            all_msg = [_("The form submission failed. Please try again later.")]
            if message:
                all_msg.append(message)
            data["form"] = {"__all__": all_msg}
        else:
            if form.is_valid():
                data["status"] = "SUCCESS"
                data["post_ident"] = form.cleaned_data.get(ALDRYN_FORMS_POST_IDENT_NAME)
                data["message"] = getattr(request, "aldryn_forms_success_message", "OK")
            else:
                data["form"] = form.errors
    else:
        data = {"status": "SKIP", "message": message}

    if request.META.get('HTTP_X_DJANGOCMS_ALDRYN_FORMS') == "SubmittedForm":
        return JsonResponse(data)

    if data.get("post_ident") is not None:
        form_plugin_instance = form_plugin.get_plugin_instance()[1]
        success_url = form_plugin_instance.get_success_url(instance=form_plugin, post_ident=data["post_ident"])
        if success_url:
            return HttpResponseRedirect(success_url)

    return None
