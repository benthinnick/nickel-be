from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.delivery import Delivery, DeliveryStatus


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    status: DeliveryStatus
    provider: str
    provider_reference: str | None
    created_at: datetime
    updated_at: datetime


def delivery_to_response(delivery: Delivery) -> DeliveryResponse:
    return DeliveryResponse(
        id=delivery.id,
        order_id=delivery.order_id,
        status=delivery.status,
        provider=delivery.provider,
        provider_reference=delivery.provider_reference,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )
