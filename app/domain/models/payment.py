from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class Payment:
    id: UUID
    order_id: UUID
    status: PaymentStatus
    provider: str
    provider_reference: str | None
    amount: Decimal
    currency: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
