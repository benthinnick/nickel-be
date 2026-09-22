from collections.abc import Mapping, MutableMapping

import httpx

from app.core.constants import REQUEST_ID_HEADER
from app.observability.request_context import get_request_id


def apply_outgoing_headers(headers: MutableMapping[str, str] | None) -> dict[str, str]:
    outgoing = dict(headers or {})
    request_id = get_request_id()
    if request_id and REQUEST_ID_HEADER not in outgoing:
        outgoing[REQUEST_ID_HEADER] = request_id
    return outgoing


def describe_request(method: str, url: str, headers: Mapping[str, str]) -> dict[str, str]:
    return {"method": method, "url": url, "request_id": headers.get(REQUEST_ID_HEADER, "-")}


def raise_for_status(response: httpx.Response) -> None:
    response.raise_for_status()
