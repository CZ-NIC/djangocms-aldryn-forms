import json
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from django.db.models import ManyToManyField

import jq
import requests
from requests.exceptions import RequestException


dataType = Dict[str, Any]

if TYPE_CHECKING:  # pragma: no cover
    from aldryn_forms.models import FormSubmissionBase

logger = logging.getLogger(__name__)


def send_to_webhook(url: str, method: str, data: dataType) -> requests.Response:
    """Send data to URL as POST."""
    if method == "JSON":
        response = requests.post(url, json.dumps(data), headers={"Content-Type": "application/json"})
    else:
        response = requests.post(url, data)
    response.raise_for_status()
    return response


def trigger_webhooks(webhooks: ManyToManyField, instance: "FormSubmissionBase", hostname: str) -> None:
    """Trigger webhooks and send them the instance data."""
    from aldryn_forms.api.serializers import FormSubmissionSerializer
    serializer = FormSubmissionSerializer(instance, context={"hostname": hostname})

    for hook in webhooks.all():
        data = transform_data(hook.transform, serializer.data)
        logger.debug(data)
        try:
            send_to_webhook(hook.url, hook.method, data)
        except RequestException as err:
            logger.error(f"{hook.url} {err}")


def transform_data(transform: Optional[List[dataType]], data: dataType) -> dataType:
    """Transform data according to rules."""
    if transform is None:
        return data
    out: dataType = {}
    for rule in transform:
        if "value" in rule:
            out[rule["dest"]] = rule["value"]
        else:
            chunks = []
            src = [rule["src"]] if isinstance(rule["src"], str) else rule["src"]
            for query in src:
                try:
                    input = jq.compile(query).input(data)
                except ValueError as err:
                    logger.error(f"{query} {err}")
                    continue
                try:
                    value = getattr(input, rule.get("fetcher", "first"))()
                except StopIteration as err:
                    logger.error(f"StopIteration {query} {err}")
                    continue
                chunks.append(str(value))
            if chunks:
                value = rule.get("sep", " ").join(chunks)
                if "match" in rule:
                    value = process_match(rule["match"], value)
                if value:
                    out[rule["dest"]] = value
    return out


def process_match(pattern: Union[str, List], value: str) -> str:
    """Process match."""
    flags = 0
    separator = " "
    if isinstance(pattern, list):
        if len(pattern) > 1:
            try:
                for flg in pattern[1]:
                    flags |= getattr(re, flg)
            except AttributeError as err:
                logger.error(f"{flg} {err}")
        if len(pattern) > 2:
            separator = pattern[2]
        pattern = pattern[0]
    try:
        match = re.match(pattern, value, flags)
    except AttributeError as err:
        logger.error(f"{pattern} {err}")
        return value
    return separator.join(match.groups())
