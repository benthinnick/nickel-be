from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ORDERS_TOPIC
from app.infrastructure.database.tables import OutboxEventRow
from app.infrastructure.kafka.schemas.events import EventEnvelope


@dataclass(frozen=True)
class OutboxEvent:
    id: UUID
    event_id: UUID
    event_type: str
    topic: str
    aggregate_id: str
    payload: dict[str, Any]
    created_at: datetime
    published_at: datetime | None


class OutboxRepository(Protocol):
    async def enqueue(
        self,
        *,
        event_type: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
        topic: str = ORDERS_TOPIC,
    ) -> UUID: ...

    async def list_unpublished(self, *, limit: int) -> list[OutboxEvent]: ...

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None: ...


class SqlOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        event_type: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
        topic: str = ORDERS_TOPIC,
    ) -> UUID:
        now = datetime.now(UTC)
        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=now,
            payload=payload,
        )
        row = OutboxEventRow(
            id=uuid4(),
            event_id=envelope.event_id,
            event_type=event_type,
            topic=topic,
            aggregate_id=str(aggregate_id),
            payload=envelope.model_dump(mode="json"),
            created_at=now,
            published_at=None,
        )
        self._session.add(row)
        await self._session.flush()
        return envelope.event_id

    async def list_unpublished(self, *, limit: int) -> list[OutboxEvent]:
        result = await self._session.scalars(
            select(OutboxEventRow)
            .where(OutboxEventRow.published_at.is_(None))
            .order_by(OutboxEventRow.created_at)
            .limit(limit)
        )
        return [_to_outbox_event(row) for row in result.all()]

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        row = await self._session.scalar(
            select(OutboxEventRow).where(OutboxEventRow.event_id == event_id)
        )
        if row is None:
            return
        row.published_at = published_at
        await self._session.flush()


def _to_outbox_event(row: OutboxEventRow) -> OutboxEvent:
    created_at = row.created_at
    published_at = row.published_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if published_at is not None and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    return OutboxEvent(
        id=row.id,
        event_id=row.event_id,
        event_type=row.event_type,
        topic=row.topic,
        aggregate_id=row.aggregate_id,
        payload=row.payload,
        created_at=created_at,
        published_at=published_at,
    )
