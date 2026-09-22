from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.delivery import Delivery, DeliveryStatus
from app.infrastructure.database.tables import DeliveryRow


class DeliveryRepository(Protocol):
    async def add(self, delivery: Delivery) -> None: ...

    async def get_by_order_id(self, order_id: UUID) -> Delivery | None: ...


class SqlDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, delivery: Delivery) -> None:
        self._session.add(
            DeliveryRow(
                id=delivery.id,
                order_id=delivery.order_id,
                status=delivery.status.value,
                provider=delivery.provider,
                provider_reference=delivery.provider_reference,
                created_at=delivery.created_at,
                updated_at=delivery.updated_at,
            )
        )
        await self._session.flush()

    async def get_by_order_id(self, order_id: UUID) -> Delivery | None:
        row = await self._session.scalar(
            select(DeliveryRow).where(DeliveryRow.order_id == order_id)
        )
        if row is None:
            return None
        return Delivery(
            id=row.id,
            order_id=row.order_id,
            status=DeliveryStatus(row.status),
            provider=row.provider,
            provider_reference=row.provider_reference,
            created_at=_ensure_utc(row.created_at),
            updated_at=_ensure_utc(row.updated_at),
        )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
