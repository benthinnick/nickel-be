from datetime import UTC, datetime
from uuid import uuid4

from app.core.constants import ORDER_DELIVERED_EVENT, ORDER_PAYMENT_SUCCEEDED_EVENT
from app.domain.models.order import OrderStatus
from app.infrastructure.clients.delivery.client import StubDeliveryClient
from app.infrastructure.kafka.handlers.order_payment_succeeded import create_handler
from app.infrastructure.kafka.schemas.events import EventEnvelope
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.processed_event_repository import SqlProcessedEventRepository
from app.repositories.product_repository import COFFEE_ID
from tests.fixtures.commerce import TEST_CART_OWNER, TEST_OWNER_KEY, make_commerce_services


async def test_payment_succeeded_handler_is_idempotent(session_factory) -> None:
    async with session_factory() as session:
        carts, _, payments, _ = make_commerce_services(session)
        await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
        order = await carts.checkout(TEST_CART_OWNER)
        payment = await payments.start_payment(order.id)
        await session.commit()

    event = EventEnvelope(
        event_id=uuid4(),
        event_type=ORDER_PAYMENT_SUCCEEDED_EVENT,
        occurred_at=datetime.now(UTC),
        payload={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "total": str(order.total),
            "currency": order.currency,
        },
    )
    handler = create_handler(session_factory, StubDeliveryClient())
    await handler(event)
    await handler(event)

    async with session_factory() as session:
        _, orders, _, deliveries = make_commerce_services(session)
        delivery = await deliveries.get_by_order_id(order.id)
        loaded_order = await orders.get_order(order.id)
        unpublished = await SqlOutboxRepository(session).list_unpublished(limit=20)
        processed = SqlProcessedEventRepository(session)
        delivered_events = [
            item for item in unpublished if item.event_type == ORDER_DELIVERED_EVENT
        ]

        assert delivery.status.value == "delivered"
        assert loaded_order.status == OrderStatus.DELIVERED
        assert len(delivered_events) == 1
        assert await processed.exists(event.event_id)
