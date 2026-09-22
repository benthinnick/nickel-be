from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

from app.core.constants import REQUEST_ID_HEADER

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_event_id: ContextVar[str | None] = ContextVar("event_id", default=None)
_kafka_topic: ContextVar[str | None] = ContextVar("kafka_topic", default=None)
_kafka_partition: ContextVar[int | None] = ContextVar("kafka_partition", default=None)
_kafka_offset: ContextVar[int | None] = ContextVar("kafka_offset", default=None)


@dataclass(frozen=True)
class RequestContext:
    request_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    event_id: str | None = None
    kafka_topic: str | None = None
    kafka_partition: int | None = None
    kafka_offset: int | None = None


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def clear_request_id() -> None:
    _request_id.set(None)


def generate_request_id() -> str:
    return str(uuid4())


def resolve_request_id(incoming: str | None) -> str:
    if incoming is not None and incoming.strip():
        return incoming.strip()
    return generate_request_id()


def set_kafka_context(
    *,
    topic: str | None = None,
    partition: int | None = None,
    offset: int | None = None,
    event_id: str | None = None,
) -> None:
    _kafka_topic.set(topic)
    _kafka_partition.set(partition)
    _kafka_offset.set(offset)
    _event_id.set(event_id)


def clear_kafka_context() -> None:
    set_kafka_context()


def get_request_context() -> RequestContext:
    return RequestContext(
        request_id=_request_id.get(),
        trace_id=_trace_id.get(),
        span_id=_span_id.get(),
        event_id=_event_id.get(),
        kafka_topic=_kafka_topic.get(),
        kafka_partition=_kafka_partition.get(),
        kafka_offset=_kafka_offset.get(),
    )


__all__ = [
    "REQUEST_ID_HEADER",
    "RequestContext",
    "clear_kafka_context",
    "clear_request_id",
    "generate_request_id",
    "get_request_context",
    "get_request_id",
    "resolve_request_id",
    "set_kafka_context",
    "set_request_id",
]
