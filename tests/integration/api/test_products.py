from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.constants import REQUEST_ID_HEADER
from app.repositories.product_repository import ARCHIVED_ID, COFFEE_ID


def test_list_products_returns_active_catalog(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/products")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 6
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 6
    assert all(item["status"] == "active" for item in body["items"])
    assert str(ARCHIVED_ID) not in {item["id"] for item in body["items"]}


def test_list_products_paginates(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/products", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 6
    assert body["limit"] == 1
    assert len(body["items"]) == 1


def test_get_product_returns_detail(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/products/{COFFEE_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(COFFEE_ID)
    assert body["sku"] == "SKU-COFFEE-250"
    assert body["currency"] == "ILS"


def test_get_product_returns_404_when_missing(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/products/{uuid4()}")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "product_not_found"
    assert "message" in body
    assert "traceback" not in body


def test_get_inactive_product_returns_404(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/products/{ARCHIVED_ID}")

    assert response.status_code == 404
    assert response.json()["code"] == "product_not_found"


def test_request_id_is_returned(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/products")

    assert response.status_code == 200
    assert REQUEST_ID_HEADER in response.headers
    assert response.headers[REQUEST_ID_HEADER]
