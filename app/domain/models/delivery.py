from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DeliveryStatus(StrEnum):
    DELIVERED = "delivered"


@dataclass(frozen=True)
class Delivery:
    id: UUID
    order_id: UUID
    status: DeliveryStatus
    provider: str
    provider_reference: str | None
    created_at: datetime
    updated_at: datetime
