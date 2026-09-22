import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability import metrics

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        logger.info(
            "HTTP request started",
            extra={"method": request.method, "path": request.url.path},
        )
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            metrics.increment("http_request_count", method=request.method, status="500")
            metrics.increment("http_error_count", method=request.method)
            metrics.observe("http_request_latency_ms", duration_ms, method=request.method)
            logger.exception("HTTP request failed")
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        status = str(response.status_code)
        metrics.increment("http_request_count", method=request.method, status=status)
        metrics.observe(
            "http_request_latency_ms",
            duration_ms,
            method=request.method,
            status=status,
        )
        if response.status_code >= 500:
            metrics.increment("http_error_count", method=request.method, status=status)
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
