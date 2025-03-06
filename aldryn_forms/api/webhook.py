"""
Sandbox: https://webhook.site/

Usage:
    from requests.exceptions import RequestException
    try:
        trigger(url, data)
    except RequestException as err:
        pass
"""
import json
import requests


def trigger(url: str, data: dict[str, str]) -> requests.Response:
    """Send data to URL as POST."""
    response = requests.post(url, json.dumps(data), headers={"Content-Type": "application/json"})
    response.raise_for_status()  # raises requests.exceptions.RequestException
    return response
