from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_delivery_service, get_order_service, get_payment_service
from app.domain.schemas.delivery import DeliveryResponse, delivery_to_response
from app.domain.schemas.order import OrderResponse, order_to_response
from app.domain.schemas.payment import PaymentResponse, payment_to_response
from app.services.delivery_service import DeliveryService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    order = await service.get_order(order_id)
    return order_to_response(order)


@router.post("/{order_id}/payments", response_model=PaymentResponse)
async def start_payment(
    order_id: UUID,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentResponse:
    payment = await service.start_payment(order_id)
    return payment_to_response(payment)


@router.get("/{order_id}/delivery", response_model=DeliveryResponse)
async def get_delivery(
    order_id: UUID,
    service: Annotated[DeliveryService, Depends(get_delivery_service)],
) -> DeliveryResponse:
    delivery = await service.get_by_order_id(order_id)
    return delivery_to_response(delivery)
