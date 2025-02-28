from typing import Any
from django.http import JsonResponse, HttpRequest

from .mixin import AuthorizedApiView


class Main(AuthorizedApiView):
    """Main API endpoint."""

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        return JsonResponse({"STATUS": "OK"})
