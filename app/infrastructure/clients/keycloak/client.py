from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings
from app.infrastructure.http.client import HttpClient


@dataclass(frozen=True)
class KeycloakUser:
    subject: str
    email: str


class KeycloakAdmin(Protocol):
    async def find_user_by_email(self, email: str) -> KeycloakUser | None: ...


class InMemoryKeycloakAdmin:
    def __init__(self) -> None:
        self._by_email: dict[str, KeycloakUser] = {}

    def add_user(self, *, subject: str, email: str) -> None:
        self._by_email[email.strip().lower()] = KeycloakUser(
            subject=subject,
            email=email.strip().lower(),
        )

    async def find_user_by_email(self, email: str) -> KeycloakUser | None:
        return self._by_email.get(email.strip().lower())


class HttpKeycloakAdmin:
    def __init__(self, settings: Settings, http_client: HttpClient) -> None:
        self._settings = settings
        self._http = http_client
        self._access_token: str | None = None

    async def find_user_by_email(self, email: str) -> KeycloakUser | None:
        if not self._settings.keycloak_admin_client_secret:
            return None
        token = await self._client_token()
        realm = self._settings.keycloak_realm
        url = f"{self._settings.keycloak_admin_url}/admin/realms/{realm}/users"
        response = await self._http.get(
            url,
            params={"email": email, "exact": "true"},
            headers={"Authorization": f"Bearer {token}"},
        )
        users = response.json()
        if not isinstance(users, list) or not users:
            return None
        record = users[0]
        subject = record.get("id")
        remote_email = record.get("email") or email
        if not isinstance(subject, str) or not subject:
            return None
        return KeycloakUser(subject=subject, email=str(remote_email).strip().lower())

    async def _client_token(self) -> str:
        if self._access_token is not None:
            return self._access_token
        realm = self._settings.keycloak_realm
        url = f"{self._settings.keycloak_admin_url}/realms/{realm}/protocol/openid-connect/token"
        response = await self._http.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._settings.keycloak_admin_client_id,
                "client_secret": self._settings.keycloak_admin_client_secret,
            },
        )
        payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            return ""
        self._access_token = token
        return token


def create_keycloak_admin(
    settings: Settings,
    http_client: HttpClient | None = None,
) -> KeycloakAdmin:
    if settings.keycloak_issuer.startswith("memory://"):
        return InMemoryKeycloakAdmin()
    if http_client is None:
        return InMemoryKeycloakAdmin()
    return HttpKeycloakAdmin(settings, http_client)
