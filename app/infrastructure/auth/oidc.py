from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.infrastructure.http.client import HttpClient

MEMORY_ISSUER = "memory://"


@dataclass(frozen=True)
class IdentityClaims:
    subject: str
    email: str


class TokenVerifier:
    def __init__(self, settings: Settings, http_client: HttpClient | None = None) -> None:
        self._settings = settings
        self._http = http_client
        self._jwks: dict[str, Any] | None = None

    async def warmup(self) -> None:
        if self._settings.keycloak_issuer.startswith(MEMORY_ISSUER):
            return
        await self._load_jwks()

    async def decode(self, token: str) -> IdentityClaims:
        if self._settings.keycloak_issuer.startswith(MEMORY_ISSUER):
            return _decode_memory_token(token, self._settings)
        jwks = await self._load_jwks()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            key = _signing_key(jwks, kid)
            payload = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                audience=self._settings.keycloak_audience,
                issuer=self._settings.keycloak_issuer,
            )
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc
        return _claims_from_payload(payload)

    async def _load_jwks(self) -> dict[str, Any]:
        if self._jwks is not None:
            return self._jwks
        if self._http is None:
            raise UnauthorizedError("Invalid or expired token")
        url = f"{self._settings.keycloak_issuer}/protocol/openid-connect/certs"
        response = await self._http.get(url)
        self._jwks = response.json()
        return self._jwks


def encode_test_token(
    *,
    subject: str,
    email: str,
    settings: Settings | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    expires_at: datetime | None = None,
) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "email": email,
        "iss": issuer if issuer is not None else MEMORY_ISSUER,
        "aud": audience if audience is not None else settings.keycloak_audience,
        "iat": int(now.timestamp()),
        "exp": int((expires_at or (now + timedelta(hours=1))).timestamp()),
    }
    return jwt.encode(payload, settings.keycloak_test_secret, algorithm="HS256")


def _decode_memory_token(token: str, settings: Settings) -> IdentityClaims:
    try:
        payload = jwt.decode(
            token,
            settings.keycloak_test_secret,
            algorithms=["HS256"],
            audience=settings.keycloak_audience,
            issuer=MEMORY_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    return _claims_from_payload(payload)


def _claims_from_payload(payload: dict[str, Any]) -> IdentityClaims:
    subject = payload.get("sub")
    email = payload.get("email")
    if not isinstance(subject, str) or not subject or not isinstance(email, str) or not email:
        raise UnauthorizedError("Invalid or expired token")
    return IdentityClaims(subject=subject, email=email)


def _signing_key(jwks: dict[str, Any], kid: str | None) -> Any:
    keys = jwks.get("keys") or []
    for jwk in keys:
        if kid is None or jwk.get("kid") == kid:
            return jwt.PyJWK.from_dict(jwk).key
    raise UnauthorizedError("Invalid or expired token")
