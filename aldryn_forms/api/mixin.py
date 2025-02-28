import binascii
from base64 import b64decode
import re
from typing import Any
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.conf import settings


class AuthorizedApiView(View):
    """Authorized API View."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        if api_token_verified(request) or basic_verified(request):
            return super().dispatch(request, *args, **kwargs)
        return JsonResponse({"error": {"message": "Not authorized."}}, status=401)


def api_token_verified(request: HttpRequest) -> bool:
    """Check API Token is valid."""
    api_token = getattr(settings, "ALDRYN_FORMS_API_TOKEN", None)
    if api_token is None:
        return False
    auth = request.headers.get('Authorization')
    if auth is None:
        return False
    match = re.match(r"Token\s+(\S+)", auth)
    if match is None:
        return False
    token = match.group(1)
    return token == api_token


def basic_verified(request: HttpRequest) -> bool:
    """Check the user and password are valid."""
    api_users = getattr(settings, "ALDRYN_FORMS_API_USERS", {})
    if not api_users:
        return False
    auth = request.headers.get('Authorization')
    if auth is None:
        return False
    match = re.match(r"Basic\s+(\S+)", auth)
    if match is None:
        return False
    try:
        token = b64decode(match.group(1)).decode()
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, password = token.split(":", 1)
    return api_users.get(username) == password
