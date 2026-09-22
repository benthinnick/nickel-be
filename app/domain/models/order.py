from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PAYMENT_FAILED = "payment_failed"
    DELIVERED = "delivered"


@dataclass(frozen=True)
class OrderItem:
    product_id: UUID
    sku: str
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass(frozen=True)
class Order:
    id: UUID
    session_id: str
    user_id: UUID | None
    status: OrderStatus
    currency: str
    total: Decimal
    items: tuple[OrderItem, ...]
    created_at: datetime
    updated_at: datetime
