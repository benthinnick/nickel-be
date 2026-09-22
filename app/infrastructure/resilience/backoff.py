import random


def exponential_backoff(
    attempt: int,
    *,
    base_seconds: float = 0.2,
    max_seconds: float = 5.0,
    jitter: bool = True,
) -> float:
    delay = min(max_seconds, base_seconds * (2**attempt))
    if jitter:
        delay = random.uniform(0, delay)
    return delay
