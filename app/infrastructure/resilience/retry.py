import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.infrastructure.resilience.backoff import exponential_backoff
from app.observability import metrics

logger = logging.getLogger(__name__)


def is_retryable(exc: BaseException) -> bool:
    return bool(getattr(exc, "retryable", False))


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    jitter: bool = True,
) -> T:
    last_error: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if not is_retryable(exc) or attempt >= max_retries:
                raise
            metrics.increment("retry_count")
            delay = exponential_backoff(attempt, jitter=jitter)
            logger.warning(
                "Retrying operation",
                extra={"attempt": attempt + 1, "delay_seconds": delay},
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error
