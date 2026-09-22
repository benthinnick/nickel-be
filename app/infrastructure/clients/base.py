from collections.abc import Awaitable, Callable
from typing import Protocol


class ExternalClient(Protocol):
    """Marker protocol for outbound service clients."""


async def execute[T](operation: Callable[[], Awaitable[T]]) -> T:
    return await operation()
