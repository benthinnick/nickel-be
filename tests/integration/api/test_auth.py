from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.infrastructure.auth.oidc import encode_test_token
from app.repositories.product_repository import COFFEE_ID, TEA_ID
from tests.fixtures.auth import auth_headers, provision_customer


def test_me_requires_bearer_token(api_client: TestClient) -> None:
    missing = api_client.get("/api/v1/customers/me")
    invalid = api_client.get(
        "/api/v1/customers/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    _, headers = provision_customer(api_client, "ada@example.com")
    me = api_client.get("/api/v1/customers/me", headers=headers)

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_expired_token_is_rejected(api_client: TestClient) -> None:
    token = encode_test_token(
        subject="ada",
        email="ada@example.com",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    response = api_client.get(
        "/api/v1/customers/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_wrong_issuer_token_is_rejected(api_client: TestClient) -> None:
    token = encode_test_token(
        subject="ada",
        email="ada@example.com",
        issuer="http://evil.example/realms/nickel",
    )
    response = api_client.get(
        "/api/v1/customers/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_first_bearer_request_provisions_customer(api_client: TestClient) -> None:
    headers = auth_headers("first@example.com")
    me = api_client.get("/api/v1/customers/me", headers=headers)
    again = api_client.get("/api/v1/customers/me", headers=headers)

    assert me.status_code == 200
    assert again.status_code == 200
    assert again.json()["id"] == me.json()["id"]


def test_authenticated_cart_is_separate_from_cookie_cart(api_client: TestClient) -> None:
    _, headers = provision_customer(api_client, "ada@example.com")
    with TestClient(api_client.app) as guest:
        guest.put(
            "/api/v1/cart/items",
            json={"product_id": str(COFFEE_ID), "quantity": 1},
        )
        api_client.put(
            "/api/v1/cart/items",
            json={"product_id": str(TEA_ID), "quantity": 2},
            headers=headers,
        )
        anonymous = guest.get("/api/v1/cart")
        authed = api_client.get("/api/v1/cart", headers=headers)

    assert anonymous.json()["items"][0]["product_id"] == str(COFFEE_ID)
    assert authed.json()["items"][0]["product_id"] == str(TEA_ID)


def test_invalid_bearer_on_cart_returns_401(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/cart", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_authenticated_request_merges_session_cart(api_client: TestClient) -> None:
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": 2},
    )
    _, headers = provision_customer(api_client, "ada@example.com")
    cart = api_client.get("/api/v1/cart", headers=headers)
    anonymous = api_client.get("/api/v1/cart")

    assert cart.json()["items"][0]["product_id"] == str(COFFEE_ID)
    assert cart.json()["items"][0]["quantity"] == 2
    assert anonymous.json()["items"] == []


def test_authenticated_checkout_sets_customer_id(api_client: TestClient) -> None:
    customer, headers = provision_customer(api_client, "ada@example.com")
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": 1},
        headers=headers,
    )
    checkout = api_client.post("/api/v1/cart/checkout", headers=headers)

    assert checkout.status_code == 201
    assert checkout.json()["customer_id"] == customer["id"]
