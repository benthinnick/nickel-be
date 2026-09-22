import time
from collections.abc import Awaitable, Callable
from enum import StrEnum

from app.observability import metrics


class CircuitOpenError(Exception):
    def __init__(self) -> None:
        super().__init__("Circuit breaker is open")
        self.retryable = False


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.name = name
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at: float | None = None

    def _can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if (
                self.opened_at is not None
                and time.monotonic() - self.opened_at >= self.recovery_timeout_seconds
            ):
                self.state = CircuitState.HALF_OPEN
                metrics.gauge("circuit_breaker_state", 0.5, name=self.name)
                return True
            return False
        return True

    def _record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None
        metrics.gauge("circuit_breaker_state", 0, name=self.name)

    def _record_failure(self) -> None:
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            metrics.gauge("circuit_breaker_state", 1, name=self.name)

    async def call[T](self, operation: Callable[[], Awaitable[T]]) -> T:
        if not self._can_attempt():
            raise CircuitOpenError()
        try:
            result = await operation()
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result
