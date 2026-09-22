from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.kafka.schemas.events import EventEnvelope, ProductCreatedPayload
from app.repositories.processed_event_repository import SqlProcessedEventRepository
from app.repositories.product_repository import SqlProductRepository
from app.services.product_service import ProductService


def create_handler(session_factory: async_sessionmaker[AsyncSession]):
    async def handle(event: EventEnvelope) -> None:
        payload = ProductCreatedPayload.model_validate(event.payload)
        async with session_factory() as session:
            processed = SqlProcessedEventRepository(session)
            try:
                if await processed.exists(event.event_id):
                    await session.commit()
                    return
                products = ProductService(SqlProductRepository(session))
                await products.apply_created(payload)
                await processed.record(event.event_id, event.event_type)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return handle
