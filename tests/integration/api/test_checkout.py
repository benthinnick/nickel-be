import asyncio

from fastapi.testclient import TestClient

from app.api.dependencies import get_payment_client
from app.core.constants import ORDER_PAYMENT_SUCCEEDED_EVENT
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.kafka.handlers import HANDLERS
from app.infrastructure.kafka.schemas.events import EventEnvelope
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.product_repository import ARCHIVED_ID, COFFEE_ID
from tests.fixtures.payments import FailingPaymentClient


def _add_coffee(api_client: TestClient, quantity: int = 1) -> None:
    response = api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": quantity},
    )
    assert response.status_code == 200


def _checkout_paid_order(api_client: TestClient) -> str:
    _add_coffee(api_client, quantity=2)
    checkout = api_client.post("/api/v1/cart/checkout")
    assert checkout.status_code == 201
    order_id = checkout.json()["id"]
    assert checkout.json()["status"] == "pending_payment"

    payment = api_client.post(f"/api/v1/orders/{order_id}/payments")
    assert payment.status_code == 200
    assert payment.json()["status"] == "succeeded"
    return order_id


def test_get_cart_sets_session_cookie(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/cart")

    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert "shekel_session" in response.cookies


def test_checkout_and_payment_flow(api_client: TestClient) -> None:
    order_id = _checkout_paid_order(api_client)

    order = api_client.get(f"/api/v1/orders/{order_id}")
    assert order.status_code == 200
    assert order.json()["status"] == "paid"
    assert "session_id" in order.json()
    assert order.json()["user_id"] is None
    assert len(order.json()["items"]) == 1
    assert order.json()["items"][0]["quantity"] == 2


def test_duplicate_checkout_returns_empty_cart(api_client: TestClient) -> None:
    _add_coffee(api_client)
    first = api_client.post("/api/v1/cart/checkout")
    second = api_client.post("/api/v1/cart/checkout")

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["code"] == "cart_empty"


def test_empty_cart_checkout_returns_400(api_client: TestClient) -> None:
    api_client.get("/api/v1/cart")
    response = api_client.post("/api/v1/cart/checkout")

    assert response.status_code == 400
    assert response.json()["code"] == "cart_empty"


def test_inactive_product_cannot_be_added(api_client: TestClient) -> None:
    response = api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(ARCHIVED_ID), "quantity": 1},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "product_not_found"


def test_repeat_payment_returns_existing(api_client: TestClient) -> None:
    order_id = _checkout_paid_order(api_client)

    first = api_client.post(f"/api/v1/orders/{order_id}/payments")
    second = api_client.post(f"/api/v1/orders/{order_id}/payments")

    assert first.json()["id"] == second.json()["id"]


def test_failed_payment_via_override(api_client: TestClient) -> None:
    api_client.app.dependency_overrides[get_payment_client] = lambda: FailingPaymentClient()
    try:
        _add_coffee(api_client)
        order_id = api_client.post("/api/v1/cart/checkout").json()["id"]

        payment = api_client.post(f"/api/v1/orders/{order_id}/payments")
        order = api_client.get(f"/api/v1/orders/{order_id}")

        assert payment.json()["status"] == "failed"
        assert order.json()["status"] == "payment_failed"
    finally:
        api_client.app.dependency_overrides.clear()


def test_payment_writes_outbox_and_handler_starts_delivery(api_client: TestClient) -> None:
    order_id = _checkout_paid_order(api_client)

    async def process_payment_succeeded() -> None:
        factory = get_session_factory()
        async with factory() as session:
            events = await SqlOutboxRepository(session).list_unpublished(limit=20)
        succeeded = [
            event for event in events if event.event_type == ORDER_PAYMENT_SUCCEEDED_EVENT
        ]
        assert len(succeeded) == 1
        envelope = EventEnvelope.model_validate(succeeded[0].payload)
        await HANDLERS[ORDER_PAYMENT_SUCCEEDED_EVENT](envelope)

    asyncio.run(process_payment_succeeded())

    delivery = api_client.get(f"/api/v1/orders/{order_id}/delivery")
    order = api_client.get(f"/api/v1/orders/{order_id}")

    assert delivery.status_code == 200
    assert delivery.json()["status"] == "delivered"
    assert order.json()["status"] == "delivered"


def test_delivery_missing_returns_404(api_client: TestClient) -> None:
    _add_coffee(api_client)
    order_id = api_client.post("/api/v1/cart/checkout").json()["id"]

    response = api_client.get(f"/api/v1/orders/{order_id}/delivery")

    assert response.status_code == 404
    assert response.json()["code"] == "delivery_not_found"
