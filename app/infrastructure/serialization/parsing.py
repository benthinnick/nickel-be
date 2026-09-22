from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID


def parse_uuid(value: str) -> UUID:
    return UUID(value)


def parse_decimal(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def utc_now() -> datetime:
    return datetime.now(UTC)
