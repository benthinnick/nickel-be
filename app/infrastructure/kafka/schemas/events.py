from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_id: UUID
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class OrderCreatedPayload(BaseModel):
    order_id: UUID
    session_id: str
    customer_id: UUID | None = None
    total: Decimal
    currency: str


class OrderPaymentSucceededPayload(BaseModel):
    order_id: UUID
    payment_id: UUID
    total: Decimal
    currency: str


class OrderPaymentFailedPayload(BaseModel):
    order_id: UUID
    payment_id: UUID
    total: Decimal
    currency: str
    failure_reason: str | None = None


class OrderDeliveredPayload(BaseModel):
    order_id: UUID
    delivery_id: UUID | None = None


class ProductCreatedPayload(BaseModel):
    product_id: UUID
    seller_id: UUID
    sku: str
    name: str
    description: str
    price: Decimal
    currency: str
    stock: int
    image_url: str | None = None
    created_by_customer_id: UUID


class ProductVisibilityPayload(BaseModel):
    product_id: UUID
    seller_id: UUID
