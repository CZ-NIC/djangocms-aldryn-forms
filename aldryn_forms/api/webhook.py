"""
Sandbox: https://webhook.site/
"""
import json
import logging
from typing import TYPE_CHECKING

import requests
from requests.exceptions import RequestException


if TYPE_CHECKING:  # pragma: no cover
    from aldryn_forms.models import FormSubmissionBase

from django.db.models import ManyToManyField


logger = logging.getLogger(__name__)


def send_to_webook(url: str, data: str) -> requests.Response:
    """Send data to URL as POST."""
    response = requests.post(url, data, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    return response


def trigger_webhooks(webhooks: ManyToManyField, instance: "FormSubmissionBase") -> None:
    """Trigger webhooks and send them the instance data."""
    from aldryn_forms.api.serializers import FormSubmissionSerializer
    serializer = FormSubmissionSerializer(instance)
    payload = json.dumps(serializer.data)
    for hook in webhooks.all():
        try:
            send_to_webook(hook.url, payload)
        except RequestException as err:
            logger.error(err)
