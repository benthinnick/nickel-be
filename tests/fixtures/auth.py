from uuid import NAMESPACE_DNS, uuid5

from fastapi.testclient import TestClient

from app.infrastructure.auth.oidc import encode_test_token


def subject_for_email(email: str) -> str:
    return str(uuid5(NAMESPACE_DNS, email.strip().lower()))


def auth_headers(email: str) -> dict[str, str]:
    token = encode_test_token(subject=subject_for_email(email), email=email)
    return {"Authorization": f"Bearer {token}"}


def provision_customer(api_client: TestClient, email: str) -> tuple[dict, dict[str, str]]:
    headers = auth_headers(email)
    response = api_client.get("/api/v1/customers/me", headers=headers)
    assert response.status_code == 200
    return response.json(), headers
