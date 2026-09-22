import pytest

from app.core.exceptions import EmailAlreadyTakenError, InvalidCredentialsError
from app.repositories.user_repository import SqlUserRepository
from app.services.user_service import UserService


def _users(db_session) -> UserService:
    return UserService(user_repository=SqlUserRepository(db_session))


async def test_register_and_authenticate(db_session) -> None:
    users = _users(db_session)

    created = await users.register(email="Ada@Example.com", password="secret123")
    loaded = await users.authenticate(email="ada@example.com", password="secret123")

    assert created.email == "ada@example.com"
    assert loaded.id == created.id


async def test_register_duplicate_email(db_session) -> None:
    users = _users(db_session)
    await users.register(email="ada@example.com", password="secret123")

    with pytest.raises(EmailAlreadyTakenError):
        await users.register(email="ADA@example.com", password="otherpass")


async def test_authenticate_rejects_bad_password(db_session) -> None:
    users = _users(db_session)
    await users.register(email="ada@example.com", password="secret123")

    with pytest.raises(InvalidCredentialsError):
        await users.authenticate(email="ada@example.com", password="wrong")
