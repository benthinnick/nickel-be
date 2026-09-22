import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import get_settings
from app.observability.request_context import get_request_context


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = get_request_context()
        settings = get_settings()
        record.request_id = context.request_id or "-"
        record.trace_id = context.trace_id or "-"
        record.span_id = context.span_id or "-"
        record.event_id = context.event_id or "-"
        record.kafka_topic = context.kafka_topic or "-"
        record.kafka_partition = (
            str(context.kafka_partition) if context.kafka_partition is not None else "-"
        )
        record.kafka_offset = str(context.kafka_offset) if context.kafka_offset is not None else "-"
        record.service = settings.app_name
        record.environment = settings.app_env
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": getattr(record, "service", "-"),
            "environment": getattr(record, "environment", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
            "event_id": getattr(record, "event_id", "-"),
            "kafka_topic": getattr(record, "kafka_topic", "-"),
            "kafka_partition": getattr(record, "kafka_partition", "-"),
            "kafka_offset": getattr(record, "kafka_offset", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    logging.getLogger("uvicorn.access").handlers.clear()
