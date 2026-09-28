from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import CartEmptyError, InsufficientStockError, ProductNotFoundError
from app.domain.models.cart import CartOwner, customer_cart_key
from app.domain.models.order import OrderStatus
from app.repositories.customer_repository import SqlCustomerRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.product_repository import ARCHIVED_ID, COFFEE_ID, TEA_ID
from app.services.customer_service import CustomerService
from tests.fixtures.commerce import (
    TEST_CART_OWNER,
    TEST_OWNER_KEY,
    TEST_SESSION_ID,
    make_commerce_services,
)


async def test_get_cart_returns_empty_when_missing(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)

    cart = await carts.get_cart(TEST_OWNER_KEY)

    assert cart.owner_key == TEST_OWNER_KEY
    assert cart.items == ()


async def test_upsert_item_adds_active_product(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)

    updated = await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=2)

    assert len(updated.items) == 1
    assert updated.items[0].product_id == COFFEE_ID
    assert updated.items[0].quantity == 2


async def test_upsert_item_rejects_inactive_product(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)

    with pytest.raises(ProductNotFoundError):
        await carts.upsert_item(TEST_OWNER_KEY, product_id=ARCHIVED_ID, quantity=1)


async def test_remove_item(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=TEA_ID, quantity=1)

    updated = await carts.remove_item(TEST_OWNER_KEY, COFFEE_ID)

    assert [item.product_id for item in updated.items] == [TEA_ID]


async def test_checkout_creates_order_and_outbox_event(db_session) -> None:
    carts, orders, _, _ = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=2)

    order = await carts.checkout(TEST_CART_OWNER)
    loaded_cart = await carts.get_cart(TEST_OWNER_KEY)
    loaded_order = await orders.get_order(order.id)
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)

    assert loaded_cart.items == ()
    assert loaded_order.status == OrderStatus.PENDING_PAYMENT
    assert loaded_order.session_id == TEST_SESSION_ID
    assert loaded_order.customer_id is None
    assert loaded_order.total == loaded_order.items[0].line_total
    assert len(unpublished) == 1
    assert unpublished[0].event_type == "order_created"
    assert unpublished[0].payload["payload"]["order_id"] == str(order.id)
    assert unpublished[0].payload["payload"]["session_id"] == TEST_SESSION_ID


async def test_checkout_rejects_empty_cart(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)

    with pytest.raises(CartEmptyError):
        await carts.checkout(TEST_CART_OWNER)


async def test_duplicate_checkout_sees_empty_cart(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    await carts.checkout(TEST_CART_OWNER)

    with pytest.raises(CartEmptyError):
        await carts.checkout(TEST_CART_OWNER)


async def test_customer_and_session_carts_are_isolated(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)
    customer_id = uuid4()
    other_customer_id = uuid4()
    customer_key = customer_cart_key(customer_id)
    other_key = customer_cart_key(other_customer_id)

    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=1)
    await carts.upsert_item(customer_key, product_id=TEA_ID, quantity=2)
    await carts.upsert_item(other_key, product_id=COFFEE_ID, quantity=4)

    session_cart = await carts.get_cart(TEST_OWNER_KEY)
    customer_cart = await carts.get_cart(customer_key)
    other_cart = await carts.get_cart(other_key)

    assert [item.product_id for item in session_cart.items] == [COFFEE_ID]
    assert [item.product_id for item in customer_cart.items] == [TEA_ID]
    assert other_cart.items[0].quantity == 4


async def test_merge_session_into_customer_sums_quantities(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)
    customer_id = uuid4()
    customer_key = customer_cart_key(customer_id)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=2)
    await carts.upsert_item(customer_key, product_id=COFFEE_ID, quantity=3)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=TEA_ID, quantity=1)

    merged = await carts.merge_session_into_customer(
        session_id=TEST_SESSION_ID, customer_id=customer_id
    )
    session_cart = await carts.get_cart(TEST_OWNER_KEY)

    by_product = {item.product_id: item.quantity for item in merged.items}
    assert by_product[COFFEE_ID] == 5
    assert by_product[TEA_ID] == 1
    assert session_cart.items == ()


async def test_checkout_with_customer_writes_customer_id(db_session) -> None:
    carts, orders, _, _ = make_commerce_services(db_session)
    customer = await CustomerService(SqlCustomerRepository(db_session)).ensure_from_identity(
        subject="kc-ada",
        email="ada@example.com",
    )
    owner = CartOwner(
        key=customer_cart_key(customer.id),
        session_id=TEST_SESSION_ID,
        customer_id=customer.id,
    )
    await carts.upsert_item(owner.key, product_id=COFFEE_ID, quantity=1)

    order = await carts.checkout(owner)
    loaded = await orders.get_order(order.id)
    unpublished = await SqlOutboxRepository(db_session).list_unpublished(limit=10)

    assert loaded.customer_id == customer.id
    assert unpublished[0].payload["payload"]["customer_id"] == str(customer.id)


async def test_upsert_rejects_quantity_above_stock(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)
    product = await carts._products.get_by_id(COFFEE_ID)
    assert product is not None
    await carts._products.save(replace(product, stock=3))

    with pytest.raises(InsufficientStockError):
        await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=4)


async def test_checkout_decrements_stock(db_session) -> None:
    carts, _, _, _ = make_commerce_services(db_session)
    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=2)
    await carts.checkout(TEST_CART_OWNER)

    await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=98)
    with pytest.raises(InsufficientStockError):
        await carts.upsert_item(TEST_OWNER_KEY, product_id=COFFEE_ID, quantity=99)
