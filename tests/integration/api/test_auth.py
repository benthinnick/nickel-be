from fastapi.testclient import TestClient

from app.repositories.product_repository import COFFEE_ID, TEA_ID


def _register(api_client: TestClient, email: str = "ada@example.com") -> dict:
    response = api_client.post(
        "/api/v1/users",
        json={"email": email, "password": "secret123"},
    )
    assert response.status_code == 201
    return response.json()


def _token(api_client: TestClient, email: str = "ada@example.com") -> str:
    response = api_client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "secret123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_register_duplicate_email_returns_409(api_client: TestClient) -> None:
    _register(api_client)
    response = api_client.post(
        "/api/v1/users",
        json={"email": "ada@example.com", "password": "secret123"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_already_taken"


def test_login_rejects_bad_password(api_client: TestClient) -> None:
    _register(api_client)
    response = api_client.post(
        "/api/v1/auth/token",
        data={"username": "ada@example.com", "password": "nope"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_me_requires_bearer_token(api_client: TestClient) -> None:
    missing = api_client.get("/api/v1/users/me")
    invalid = api_client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    _register(api_client)
    token = _token(api_client)
    me = api_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_authenticated_cart_is_separate_from_cookie_cart(api_client: TestClient) -> None:
    _register(api_client)
    token = _token(api_client)
    headers = {"Authorization": f"Bearer {token}"}
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": 1},
    )
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(TEA_ID), "quantity": 2},
        headers=headers,
    )

    anonymous = api_client.get("/api/v1/cart")
    authed = api_client.get("/api/v1/cart", headers=headers)

    assert anonymous.json()["items"][0]["product_id"] == str(COFFEE_ID)
    assert authed.json()["items"][0]["product_id"] == str(TEA_ID)


def test_invalid_bearer_on_cart_returns_401(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/cart", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_login_merges_session_cart_into_user_cart(api_client: TestClient) -> None:
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": 2},
    )
    _register(api_client)
    token = _token(api_client)
    cart = api_client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})

    anonymous = api_client.get("/api/v1/cart")

    assert cart.json()["items"][0]["product_id"] == str(COFFEE_ID)
    assert cart.json()["items"][0]["quantity"] == 2
    assert anonymous.json()["items"] == []


def test_authenticated_checkout_sets_user_id(api_client: TestClient) -> None:
    user = _register(api_client)
    token = _token(api_client)
    headers = {"Authorization": f"Bearer {token}"}
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": 1},
        headers=headers,
    )
    checkout = api_client.post("/api/v1/cart/checkout", headers=headers)

    assert checkout.status_code == 201
    assert checkout.json()["user_id"] == user["id"]
