from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.clients.delivery.client import DeliveryClient
from app.infrastructure.kafka.schemas.events import EventEnvelope, OrderPaymentSucceededPayload
from app.repositories.delivery_repository import SqlDeliveryRepository
from app.repositories.order_repository import SqlOrderRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.processed_event_repository import SqlProcessedEventRepository
from app.services.delivery_service import DeliveryService
from app.services.order_service import OrderService


def create_handler(
    session_factory: async_sessionmaker[AsyncSession],
    delivery_client: DeliveryClient,
):
    async def handle(event: EventEnvelope) -> None:
        payload = OrderPaymentSucceededPayload.model_validate(event.payload)
        async with session_factory() as session:
            processed = SqlProcessedEventRepository(session)
            try:
                if await processed.exists(event.event_id):
                    await session.commit()
                    return
                orders = SqlOrderRepository(session)
                outbox = SqlOutboxRepository(session)
                delivery_service = DeliveryService(
                    order_repository=orders,
                    delivery_repository=SqlDeliveryRepository(session),
                    outbox_repository=outbox,
                    order_service=OrderService(
                        order_repository=orders,
                        outbox_repository=outbox,
                    ),
                    delivery_client=delivery_client,
                )
                await delivery_service.start_for_order(payload.order_id)
                await processed.record(event.event_id, event.event_type)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return handle
