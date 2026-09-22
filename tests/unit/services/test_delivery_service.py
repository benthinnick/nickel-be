from app.core.constants import ORDER_DELIVERED_EVENT
from app.domain.models.delivery import DeliveryStatus
from app.domain.models.order import OrderStatus
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.product_repository import COFFEE_ID
from tests.fixtures.commerce import TEST_CART_OWNER, TEST_OWNER_KEY, make_commerce_services


async def test_start_delivery_after_payment(db_session) -> None:
    carts, orders, payments, deliveries = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    order = await carts.checkout(TEST_CART_OWNER)
    await payments.start_payment(order.id)

    delivery = await deliveries.start_for_order(order.id)
    loaded_order = await orders.get_order(order.id)
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)

    assert delivery is not None
    assert delivery.status == DeliveryStatus.DELIVERED
    assert loaded_order.status == OrderStatus.DELIVERED
    assert any(event.event_type == ORDER_DELIVERED_EVENT for event in unpublished)


async def test_start_delivery_is_idempotent(db_session) -> None:
    carts, _, payments, deliveries = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    order = await carts.checkout(TEST_CART_OWNER)
    await payments.start_payment(order.id)

    first = await deliveries.start_for_order(order.id)
    second = await deliveries.start_for_order(order.id)
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)
    delivered_events = [
        event for event in unpublished if event.event_type == ORDER_DELIVERED_EVENT
    ]

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert len(delivered_events) == 1


async def test_start_delivery_skips_unpaid_order(db_session) -> None:
    carts, _, _, deliveries = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    order = await carts.checkout(TEST_CART_OWNER)

    result = await deliveries.start_for_order(order.id)

    assert result is None
