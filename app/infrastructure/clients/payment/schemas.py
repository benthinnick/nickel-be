from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class ChargeRequest:
    payment_id: UUID
    order_id: UUID
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class ChargeResponse:
    succeeded: bool
    provider: str
    provider_reference: str | None
    failure_reason: str | None = None
