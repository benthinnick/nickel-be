from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    email: str


def create_access_token(
    *,
    user_id: UUID,
    email: str,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> AccessTokenClaims:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    subject = payload.get("sub")
    email = payload.get("email")
    if not isinstance(subject, str) or not isinstance(email, str):
        raise UnauthorizedError("Invalid or expired token")
    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    return AccessTokenClaims(user_id=user_id, email=email)
