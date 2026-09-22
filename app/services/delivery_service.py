from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.constants import ORDER_DELIVERED_EVENT
from app.core.exceptions import DeliveryNotFoundError, OrderNotFoundError
from app.domain.models.delivery import Delivery, DeliveryStatus
from app.domain.models.order import OrderStatus
from app.infrastructure.clients.delivery.client import DeliveryClient
from app.infrastructure.clients.delivery.schemas import DispatchRequest
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.order_service import OrderService


class DeliveryService:
    def __init__(
        self,
        order_repository: OrderRepository,
        delivery_repository: DeliveryRepository,
        outbox_repository: OutboxRepository,
        order_service: OrderService,
        delivery_client: DeliveryClient,
    ) -> None:
        self._orders = order_repository
        self._deliveries = delivery_repository
        self._outbox = outbox_repository
        self._order_service = order_service
        self._delivery_client = delivery_client

    async def start_for_order(self, order_id: UUID) -> Delivery | None:
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)

        existing = await self._deliveries.get_by_order_id(order_id)
        if existing is not None:
            return existing

        if order.status not in {OrderStatus.PAID, OrderStatus.DELIVERED}:
            return None

        delivery_id = uuid4()
        dispatch = await self._delivery_client.dispatch(
            DispatchRequest(delivery_id=delivery_id, order_id=order_id)
        )
        now = datetime.now(UTC)
        delivery = Delivery(
            id=delivery_id,
            order_id=order_id,
            status=DeliveryStatus(dispatch.status),
            provider=dispatch.provider,
            provider_reference=dispatch.provider_reference,
            created_at=now,
            updated_at=now,
        )
        await self._deliveries.add(delivery)
        await self._order_service.mark_delivered(order_id)
        await self._outbox.enqueue(
            event_type=ORDER_DELIVERED_EVENT,
            aggregate_id=order_id,
            payload={
                "order_id": str(order_id),
                "delivery_id": str(delivery.id),
            },
        )
        return delivery

    async def get_by_order_id(self, order_id: UUID) -> Delivery:
        delivery = await self._deliveries.get_by_order_id(order_id)
        if delivery is None:
            raise DeliveryNotFoundError(order_id=order_id)
        return delivery
