from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.kafka.schemas.events import EventEnvelope, OrderDeliveredPayload
from app.repositories.order_repository import SqlOrderRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.processed_event_repository import SqlProcessedEventRepository
from app.services.order_service import OrderService


def create_handler(session_factory: async_sessionmaker[AsyncSession]):
    async def handle(event: EventEnvelope) -> None:
        payload = OrderDeliveredPayload.model_validate(event.payload)
        async with session_factory() as session:
            processed = SqlProcessedEventRepository(session)
            try:
                if await processed.exists(event.event_id):
                    await session.commit()
                    return
                order_service = OrderService(
                    order_repository=SqlOrderRepository(session),
                    outbox_repository=SqlOutboxRepository(session),
                )
                await order_service.mark_delivered(payload.order_id)
                await processed.record(event.event_id, event.event_type)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return handle
