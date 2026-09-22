"""No-op metrics hooks shared across API, Kafka, and HTTP clients."""


def increment(name: str, value: int = 1, **labels: str) -> None:
    return None


def observe(name: str, value: float, **labels: str) -> None:
    return None


def gauge(name: str, value: float, **labels: str) -> None:
    return None
