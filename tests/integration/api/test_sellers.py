from fastapi.testclient import TestClient

from app.repositories.product_repository import COFFEE_ID


def _register(api_client: TestClient, email: str) -> dict:
    response = api_client.post(
        "/api/v1/users",
        json={"email": email, "password": "secret123"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(api_client: TestClient, email: str) -> dict[str, str]:
    token = api_client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "secret123"},
    )
    assert token.status_code == 200
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def _create_seller(
    api_client: TestClient,
    headers: dict[str, str],
    name: str = "Ada Market",
) -> dict:
    response = api_client.post("/api/v1/sellers", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_outsider_cannot_change_seller_products(api_client: TestClient) -> None:
    _register(api_client, "owner@example.com")
    _register(api_client, "outsider@example.com")
    owner = _headers(api_client, "owner@example.com")
    outsider = _headers(api_client, "outsider@example.com")
    seller = _create_seller(api_client, owner)
    created = api_client.post(
        f"/api/v1/sellers/{seller['id']}/products",
        json={
            "sku": "SKU-SUMAC",
            "name": "Sumac",
            "description": "Tangy",
            "price": "12.00",
            "stock": 4,
        },
        headers=owner,
    )
    assert created.status_code == 202

    forbidden = api_client.post(
        f"/api/v1/sellers/{seller['id']}/products/{created.json()['product_id']}/stock",
        json={"delta": 1},
        headers=outsider,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"


def test_member_creates_product_via_event_and_it_is_public(api_client: TestClient) -> None:
    _register(api_client, "owner@example.com")
    _register(api_client, "member@example.com")
    owner = _headers(api_client, "owner@example.com")
    member = _headers(api_client, "member@example.com")
    seller = _create_seller(api_client, owner)
    invite = api_client.post(
        f"/api/v1/sellers/{seller['id']}/members",
        json={"email": "member@example.com"},
        headers=owner,
    )
    assert invite.status_code == 201

    created = api_client.post(
        f"/api/v1/sellers/{seller['id']}/products",
        json={
            "sku": "SKU-ZAATAR",
            "name": "Zaatar Blend",
            "description": "House blend",
            "price": "22.00",
            "stock": 9,
        },
        headers=member,
    )
    assert created.status_code == 202
    product_id = created.json()["product_id"]

    public = api_client.get(f"/api/v1/products/{product_id}")
    assert public.status_code == 200
    assert public.json()["name"] == "Zaatar Blend"
    assert public.json()["seller_id"] == seller["id"]
    assert public.json()["stock"] == 9


def test_hide_removes_product_from_public_catalog(api_client: TestClient) -> None:
    _register(api_client, "owner@example.com")
    owner = _headers(api_client, "owner@example.com")
    seller = _create_seller(api_client, owner)
    created = api_client.post(
        f"/api/v1/sellers/{seller['id']}/products",
        json={
            "sku": "SKU-HIDDEN",
            "name": "Hidden Spice",
            "description": "Soon gone",
            "price": "8.00",
            "stock": 3,
        },
        headers=owner,
    )
    product_id = created.json()["product_id"]
    hidden = api_client.post(
        f"/api/v1/sellers/{seller['id']}/products/{product_id}/hide",
        headers=owner,
    )
    assert hidden.status_code == 200
    assert hidden.json()["status"] == "inactive"
    assert api_client.get(f"/api/v1/products/{product_id}").status_code == 404


def test_seeded_catalog_still_supports_anonymous_checkout(api_client: TestClient) -> None:
    api_client.put(
        "/api/v1/cart/items",
        json={"product_id": str(COFFEE_ID), "quantity": 1},
    )
    checkout = api_client.post("/api/v1/cart/checkout")

    assert checkout.status_code == 201
    assert checkout.json()["user_id"] is None
