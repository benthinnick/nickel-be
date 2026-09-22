from dataclasses import dataclass
from uuid import UUID

from app.domain.models.delivery import DeliveryStatus


@dataclass(frozen=True)
class DispatchRequest:
    delivery_id: UUID
    order_id: UUID


@dataclass(frozen=True)
class DispatchResponse:
    provider: str
    provider_reference: str
    status: DeliveryStatus
