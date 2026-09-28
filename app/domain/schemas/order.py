from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.order import Order, OrderStatus


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    sku: str
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: str
    customer_id: UUID | None
    status: OrderStatus
    currency: str
    total: Decimal
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime


def order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        session_id=order.session_id,
        customer_id=order.customer_id,
        status=order.status,
        currency=order.currency,
        total=order.total,
        items=[
            OrderItemResponse(
                product_id=item.product_id,
                sku=item.sku,
                name=item.name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                line_total=item.line_total,
            )
            for item in order.items
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
