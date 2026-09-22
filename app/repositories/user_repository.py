from dataclasses import dataclass
from datetime import UTC
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.user import User
from app.infrastructure.database.tables import UserRow


@dataclass(frozen=True)
class UserAccount:
    user: User
    password_hash: str


class UserRepository(Protocol):
    async def add(self, user: User, *, password_hash: str) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_account_by_email(self, email: str) -> UserAccount | None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User, *, password_hash: str) -> None:
        self._session.add(
            UserRow(
                id=user.id,
                email=user.email,
                password_hash=password_hash,
                created_at=user.created_at,
            )
        )
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return _to_user(row) if row is not None else None

    async def get_account_by_email(self, email: str) -> UserAccount | None:
        row = await self._session.scalar(select(UserRow).where(UserRow.email == email))
        if row is None:
            return None
        return UserAccount(user=_to_user(row), password_hash=row.password_hash)

    async def get_by_email(self, email: str) -> User | None:
        account = await self.get_account_by_email(email)
        return account.user if account is not None else None


def _to_user(row: UserRow) -> User:
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return User(id=row.id, email=row.email, created_at=created_at)
