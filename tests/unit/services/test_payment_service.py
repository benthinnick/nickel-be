from app.core.constants import ORDER_CREATED_EVENT, ORDER_PAYMENT_SUCCEEDED_EVENT
from app.domain.models.order import OrderStatus
from app.domain.models.payment import PaymentStatus
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.product_repository import COFFEE_ID
from tests.fixtures.commerce import TEST_CART_OWNER, TEST_OWNER_KEY, make_commerce_services
from tests.fixtures.payments import FailingPaymentClient


async def test_start_payment_marks_order_paid(db_session) -> None:
    carts, orders, payments, _ = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    order = await carts.checkout(TEST_CART_OWNER)

    payment = await payments.start_payment(order.id)
    loaded = await orders.get_order(order.id)
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)
    types = {event.event_type for event in unpublished}

    assert payment.status == PaymentStatus.SUCCEEDED
    assert loaded.status == OrderStatus.PAID
    assert ORDER_CREATED_EVENT in types
    assert ORDER_PAYMENT_SUCCEEDED_EVENT in types


async def test_start_payment_is_idempotent(db_session) -> None:
    carts, _, payments, _ = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    order = await carts.checkout(TEST_CART_OWNER)

    first = await payments.start_payment(order.id)
    second = await payments.start_payment(order.id)

    assert first.id == second.id
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)
    succeeded = [
        event for event in unpublished if event.event_type == ORDER_PAYMENT_SUCCEEDED_EVENT
    ]
    assert len(succeeded) == 1


async def test_failed_payment_marks_order_failed(db_session) -> None:
    carts, orders, payments, _ = make_commerce_services(
        db_session,
        payment_client=FailingPaymentClient(),
    )
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    order = await carts.checkout(TEST_CART_OWNER)

    payment = await payments.start_payment(order.id)
    loaded = await orders.get_order(order.id)
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)

    assert payment.status == PaymentStatus.FAILED
    assert payment.failure_reason == "declined"
    assert loaded.status == OrderStatus.PAYMENT_FAILED
    assert any(event.event_type == "order_payment_failed" for event in unpublished)
