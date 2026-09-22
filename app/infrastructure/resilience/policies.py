from dataclasses import dataclass

from app.core.config import get_settings
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker


@dataclass(frozen=True)
class ResiliencePolicy:
    timeout_seconds: float = 5.0
    max_retries: int = 3
    backoff: str = "exponential"
    jitter: bool = True
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: float = 30.0


def default_policy() -> ResiliencePolicy:
    settings = get_settings()
    return ResiliencePolicy(
        timeout_seconds=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
        circuit_breaker_failure_threshold=settings.circuit_breaker_failure_threshold,
        circuit_breaker_recovery_timeout_seconds=settings.circuit_breaker_recovery_timeout_seconds,
    )


def no_retry_policy() -> ResiliencePolicy:
    return ResiliencePolicy(max_retries=0, circuit_breaker_enabled=False)


def build_circuit_breaker(policy: ResiliencePolicy, *, name: str) -> CircuitBreaker | None:
    if not policy.circuit_breaker_enabled:
        return None
    return CircuitBreaker(
        failure_threshold=policy.circuit_breaker_failure_threshold,
        recovery_timeout_seconds=policy.circuit_breaker_recovery_timeout_seconds,
        name=name,
    )
