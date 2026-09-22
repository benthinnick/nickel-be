from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models.order import Order, OrderItem, OrderStatus
from app.infrastructure.database.tables import OrderItemRow, OrderRow


class OrderRepository(Protocol):
    async def add(self, order: Order) -> None: ...

    async def get_by_id(self, order_id: UUID) -> Order | None: ...

    async def save(self, order: Order) -> None: ...


class SqlOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order) -> None:
        row = OrderRow(
            id=order.id,
            session_id=order.session_id,
            user_id=order.user_id,
            status=order.status.value,
            currency=order.currency,
            total=order.total,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        for item in order.items:
            row.items.append(
                OrderItemRow(
                    id=uuid4(),
                    order_id=order.id,
                    product_id=item.product_id,
                    sku=item.sku,
                    name=item.name,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    line_total=item.line_total,
                )
            )
        self._session.add(row)
        await self._session.flush()

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self._session.scalar(
            select(OrderRow)
            .options(selectinload(OrderRow.items))
            .where(OrderRow.id == order_id)
        )
        if result is None:
            return None
        return _to_order(result)

    async def save(self, order: Order) -> None:
        row = await self._session.get(OrderRow, order.id)
        if row is None:
            await self.add(order)
            return
        row.status = order.status.value
        row.updated_at = order.updated_at
        await self._session.flush()


def _to_order(row: OrderRow) -> Order:
    return Order(
        id=row.id,
        session_id=row.session_id,
        user_id=row.user_id,
        status=OrderStatus(row.status),
        currency=row.currency,
        total=Decimal(row.total),
        items=tuple(
            OrderItem(
                product_id=item.product_id,
                sku=item.sku,
                name=item.name,
                unit_price=Decimal(item.unit_price),
                quantity=item.quantity,
                line_total=Decimal(item.line_total),
            )
            for item in row.items
        ),
        created_at=_ensure_utc(row.created_at),
        updated_at=_ensure_utc(row.updated_at),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
