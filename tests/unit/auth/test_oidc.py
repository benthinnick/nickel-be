import pytest

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.infrastructure.auth.oidc import TokenVerifier, encode_test_token


def _settings() -> Settings:
    return Settings(
        keycloak_issuer="memory://",
        keycloak_audience="shekel-api",
        keycloak_test_secret="unit-oidc-secret-at-least-32-bytes",
    )


async def test_memory_token_round_trip() -> None:
    settings = _settings()
    token = encode_test_token(
        subject="kc-ada",
        email="ada@example.com",
        settings=settings,
    )
    claims = await TokenVerifier(settings).decode(token)

    assert claims.subject == "kc-ada"
    assert claims.email == "ada@example.com"


async def test_memory_token_rejects_wrong_audience() -> None:
    settings = _settings()
    token = encode_test_token(
        subject="kc-ada",
        email="ada@example.com",
        settings=settings,
        audience="other-api",
    )

    with pytest.raises(UnauthorizedError):
        await TokenVerifier(settings).decode(token)
