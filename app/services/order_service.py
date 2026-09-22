from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.constants import ORDER_CREATED_EVENT
from app.core.exceptions import OrderNotFoundError
from app.domain.models.order import Order, OrderItem, OrderStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        outbox_repository: OutboxRepository,
    ) -> None:
        self._orders = order_repository
        self._outbox = outbox_repository

    async def create_from_checkout(
        self,
        *,
        session_id: str,
        user_id: UUID | None = None,
        items: tuple[OrderItem, ...],
        currency: str,
        total: Decimal,
    ) -> Order:
        now = datetime.now(UTC)
        order = Order(
            id=uuid4(),
            session_id=session_id,
            user_id=user_id,
            status=OrderStatus.PENDING_PAYMENT,
            currency=currency,
            total=total,
            items=items,
            created_at=now,
            updated_at=now,
        )
        await self._orders.add(order)
        payload = {
            "order_id": str(order.id),
            "session_id": order.session_id,
            "total": str(order.total),
            "currency": order.currency,
        }
        if order.user_id is not None:
            payload["user_id"] = str(order.user_id)
        await self._outbox.enqueue(
            event_type=ORDER_CREATED_EVENT,
            aggregate_id=order.id,
            payload=payload,
        )
        return order

    async def get_order(self, order_id: UUID) -> Order:
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    async def mark_paid(self, order_id: UUID) -> Order:
        order = await self.get_order(order_id)
        if order.status in {OrderStatus.PAID, OrderStatus.DELIVERED}:
            return order
        if order.status != OrderStatus.PENDING_PAYMENT:
            return order
        updated = replace(order, status=OrderStatus.PAID, updated_at=datetime.now(UTC))
        await self._orders.save(updated)
        return updated

    async def mark_payment_failed(self, order_id: UUID) -> Order:
        order = await self.get_order(order_id)
        if order.status == OrderStatus.PAYMENT_FAILED:
            return order
        if order.status != OrderStatus.PENDING_PAYMENT:
            return order
        updated = replace(
            order,
            status=OrderStatus.PAYMENT_FAILED,
            updated_at=datetime.now(UTC),
        )
        await self._orders.save(updated)
        return updated

    async def mark_delivered(self, order_id: UUID) -> Order:
        order = await self.get_order(order_id)
        if order.status == OrderStatus.DELIVERED:
            return order
        if order.status != OrderStatus.PAID:
            return order
        updated = replace(order, status=OrderStatus.DELIVERED, updated_at=datetime.now(UTC))
        await self._orders.save(updated)
        return updated
