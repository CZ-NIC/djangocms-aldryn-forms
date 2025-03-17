# import markdown
from typing import Callable, Dict, Optional, Tuple, Union

from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.utils.deprecation import MiddlewareMixin

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
            return get_response(request)

        # The following code is written according to the function submit_form_view in views.py.
        form_plugin_id = request.POST.get('form_plugin_id')
        if form_plugin_id is None:
            return get_response(request)
        if not form_plugin_id.isdigit():
            return get_response(request)

        try:
            form_plugin = get_plugin_tree(FormPlugin, pk=form_plugin_id)
        except FormPlugin.DoesNotExist:
            return get_response(request)

        form_plugin_instance = form_plugin.get_plugin_instance()[1]
        form = form_plugin_instance.process_form(form_plugin, request)

        return get_response(request, (form_plugin, form))


def get_response(
    request: HttpRequest,
    form_plugin_and_form: Tuple[FormPlugin, FormSubmissionBaseForm] = None,
) -> Optional[Union[HttpResponseRedirect, JsonResponse]]:
    """Get response type."""
    if form_plugin_and_form is None:
        return None
    form_plugin, form = form_plugin_and_form

    data: dict[str, str] = {"status": "ERROR"}
    if form.is_valid():
        data["status"] = "SUCCESS"
        data["post_ident"] = form.cleaned_data.get(ALDRYN_FORMS_POST_IDENT_NAME)
        data["message"] = getattr(request, "aldryn_forms_success_message", "OK")
    else:
        data["form"] = form.errors

    if request.META.get('HTTP_X_REQUESTED_WITH') == "XMLHttpRequest":
        return JsonResponse(data)

    if data["status"] == "SUCCESS":
        form_plugin_instance = form_plugin.get_plugin_instance()[1]
        success_url = form_plugin_instance.get_success_url(instance=form_plugin, post_ident=data.get("post_ident"))
        if success_url:
            return HttpResponseRedirect(success_url)

    return None
