import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def _default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dumps(value: Any) -> str:
    return json.dumps(value, default=_default)


def loads(value: str | bytes) -> Any:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)
