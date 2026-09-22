from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import EmailAlreadyTakenError, InvalidCredentialsError, UnauthorizedError
from app.domain.models.user import User
from app.infrastructure.auth.password import hash_password, verify_password
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def register(self, *, email: str, password: str) -> User:
        normalized = _normalize_email(email)
        existing = await self._users.get_account_by_email(normalized)
        if existing is not None:
            raise EmailAlreadyTakenError(normalized)
        user = User(id=uuid4(), email=normalized, created_at=datetime.now(UTC))
        await self._users.add(user, password_hash=hash_password(password))
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        account = await self._users.get_account_by_email(_normalize_email(email))
        if account is None or not verify_password(password, account.password_hash):
            raise InvalidCredentialsError()
        return account.user

    async def get_by_id(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Invalid or expired token")
        return user


def _normalize_email(email: str) -> str:
    return email.strip().lower()
