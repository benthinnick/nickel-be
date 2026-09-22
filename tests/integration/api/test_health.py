from fastapi.testclient import TestClient


def test_health(api_client: TestClient) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body
