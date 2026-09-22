from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.infrastructure.http.errors import (
    HttpConnectionError,
    HttpStatusError,
    HttpTimeoutError,
    is_retryable_status,
)
from app.infrastructure.http.middleware import apply_outgoing_headers
from app.observability import metrics


class HttpClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        outgoing_headers = apply_outgoing_headers(headers)
        metrics.increment("external_api_request_count", method=method)
        try:
            response = await self._client.request(
                method,
                url,
                headers=outgoing_headers,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            metrics.increment("external_api_failures", reason="timeout")
            raise HttpTimeoutError() from exc
        except httpx.TransportError as exc:
            metrics.increment("external_api_failures", reason="connection")
            raise HttpConnectionError() from exc

        if response.is_error:
            retryable = is_retryable_status(response.status_code)
            metrics.increment(
                "external_api_failures",
                reason="status",
                status=str(response.status_code),
            )
            raise HttpStatusError(
                f"HTTP {response.status_code} from {url}",
                status_code=response.status_code,
                retryable=retryable,
            )
        return response

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()


def create_http_client(settings: Settings | None = None) -> HttpClient:
    settings = settings or get_settings()
    return HttpClient(
        httpx.AsyncClient(
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": settings.app_name},
        )
    )
