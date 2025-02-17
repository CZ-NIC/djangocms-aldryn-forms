from typing import Callable, Dict, Optional, Tuple

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from aldryn_forms.models import FormPlugin
from aldryn_forms.utils import get_plugin_tree


class HandleHttpPost(MiddlewareMixin):
    """Handle HTTP POST."""

    def process_view(
        self, request: HttpRequest, callback: Callable, callback_args: Tuple[str, ...], callback_kwargs: Dict[str, str]
    ) -> Optional[HttpResponse]:
        """Process view when request method is POST and when the form plugin is found."""

        if request.method != 'POST':
            return None

        # The following code is written according to the function submit_form_view in views.py.
        form_plugin_id = request.POST.get('form_plugin_id')
        if form_plugin_id is None:
            return None
        if not form_plugin_id.isdigit():
            return None

        try:
            form_plugin = get_plugin_tree(FormPlugin, pk=form_plugin_id)
        except FormPlugin.DoesNotExist:
            return None

        form_plugin_instance = form_plugin.get_plugin_instance()[1]
        form = form_plugin_instance.process_form(form_plugin, request)
        success_url = form_plugin_instance.get_success_url(instance=form_plugin, post_ident=form.instance.post_ident)

        if form.is_valid():
            if request.META.get('HTTP_X_REQUESTED_WITH') == "XMLHttpRequest":
                return JsonResponse({"post_ident": form.instance.post_ident})
            if success_url:
                return HttpResponseRedirect(success_url)
        else:
            print(form.errors)
            if request.META.get('HTTP_X_REQUESTED_WITH') == "XMLHttpRequest":
                return JsonResponse(form.errors.as_json())

        return None
