from fastapi.testclient import TestClient

from tests.fixtures.auth import provision_customer


def _headers(api_client: TestClient, email: str) -> dict[str, str]:
    _, headers = provision_customer(api_client, email)
    return headers


def test_search_finds_seeded_product_by_name(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/products/search", params={"q": "Coffee"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any("Coffee" in item["name"] for item in body["items"])


def test_created_product_is_searchable_then_hidden(api_client: TestClient) -> None:
    _headers(api_client, "owner@example.com")
    owner = _headers(api_client, "owner@example.com")
    seller = api_client.post("/api/v1/sellers", json={"name": "Search Shop"}, headers=owner)
    assert seller.status_code == 201
    seller_id = seller.json()["id"]
    created = api_client.post(
        f"/api/v1/sellers/{seller_id}/products",
        json={
            "sku": "SKU-SEARCH",
            "name": "Unique Fenugreek",
            "description": "Rare",
            "price": "11.00",
            "stock": 5,
        },
        headers=owner,
    )
    assert created.status_code == 202
    product_id = created.json()["product_id"]

    found = api_client.get("/api/v1/products/search", params={"q": "Fenugreek"})
    assert found.status_code == 200
    assert found.json()["total"] == 1
    assert found.json()["items"][0]["id"] == product_id

    hidden = api_client.post(
        f"/api/v1/sellers/{seller_id}/products/{product_id}/hide",
        headers=owner,
    )
    assert hidden.status_code == 200
    missing = api_client.get("/api/v1/products/search", params={"q": "Fenugreek"})
    assert missing.json()["total"] == 0

    shown = api_client.post(
        f"/api/v1/sellers/{seller_id}/products/{product_id}/unhide",
        headers=owner,
    )
    assert shown.status_code == 200
    restored = api_client.get("/api/v1/products/search", params={"q": "Fenugreek"})
    assert restored.json()["total"] == 1
    assert restored.json()["items"][0]["id"] == product_id


def test_autocomplete_returns_seeded_coffee_name(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/products/search/autocomplete", params={"q": "cof"})

    assert response.status_code == 200
    queries = response.json()["queries"]
    assert "Ethiopian Coffee Beans" in queries
    assert len(queries) <= 5


def test_autocomplete_stops_suggesting_hidden_product(api_client: TestClient) -> None:
    _headers(api_client, "owner@example.com")
    owner = _headers(api_client, "owner@example.com")
    seller = api_client.post("/api/v1/sellers", json={"name": "Hide Shop"}, headers=owner)
    assert seller.status_code == 201
    seller_id = seller.json()["id"]
    created = api_client.post(
        f"/api/v1/sellers/{seller_id}/products",
        json={
            "sku": "SKU-AUTO",
            "name": "Unique Cardamom Pods",
            "description": "Rare",
            "price": "9.00",
            "stock": 4,
        },
        headers=owner,
    )
    assert created.status_code == 202
    product_id = created.json()["product_id"]

    found = api_client.get("/api/v1/products/search/autocomplete", params={"q": "cardam"})
    assert found.status_code == 200
    assert "Unique Cardamom Pods" in found.json()["queries"]

    hidden = api_client.post(
        f"/api/v1/sellers/{seller_id}/products/{product_id}/hide",
        headers=owner,
    )
    assert hidden.status_code == 200
    missing = api_client.get("/api/v1/products/search/autocomplete", params={"q": "cardam"})
    assert "Unique Cardamom Pods" not in missing.json()["queries"]
