import asyncio
from collections.abc import Awaitable


class TimeoutExceededError(Exception):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"Operation timed out after {seconds} seconds")
        self.seconds = seconds
        self.retryable = True


async def with_timeout[T](awaitable: Awaitable[T], seconds: float) -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=seconds)
    except TimeoutError as exc:
        raise TimeoutExceededError(seconds) from exc
