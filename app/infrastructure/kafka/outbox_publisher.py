import asyncio
import logging
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.observability import metrics
from app.repositories.outbox_repository import SqlOutboxRepository

logger = logging.getLogger(__name__)


class MessagePublisher(Protocol):
    async def publish(self, topic: str, value: dict, *, key: str | None = None) -> None: ...


class OutboxPublisher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        producer: MessagePublisher,
        *,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 50,
    ) -> None:
        self._session_factory = session_factory
        self._producer = producer
        self._poll_interval_seconds = poll_interval_seconds
        self._batch_size = batch_size

    async def publish_pending(self) -> int:
        async with self._session_factory() as session:
            repository = SqlOutboxRepository(session)
            events = await repository.list_unpublished(limit=self._batch_size)
            published = 0
            now = datetime.now(UTC)
            for event in events:
                await self._producer.publish(
                    event.topic,
                    event.payload,
                    key=event.aggregate_id,
                )
                await repository.mark_published(event.event_id, now)
                published += 1
            await session.commit()
            if published:
                metrics.increment("outbox_events_published", published)
            return published

    async def run(self) -> None:
        logger.info("Outbox publisher started")
        try:
            while True:
                try:
                    await self.publish_pending()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Outbox publisher failed to publish batch")
                await asyncio.sleep(self._poll_interval_seconds)
        finally:
            logger.info("Outbox publisher stopped")
