from datetime import UTC
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.customer import Customer
from app.infrastructure.database.tables import CustomerRow


class CustomerRepository(Protocol):
    async def add(self, customer: Customer) -> None: ...

    async def get_by_id(self, customer_id: UUID) -> Customer | None: ...

    async def get_by_keycloak_sub(self, keycloak_sub: str) -> Customer | None: ...

    async def get_by_email(self, email: str) -> Customer | None: ...

    async def update_email(self, customer_id: UUID, email: str) -> None: ...


class SqlCustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, customer: Customer) -> None:
        self._session.add(
            CustomerRow(
                id=customer.id,
                keycloak_sub=customer.keycloak_sub,
                email=customer.email,
                created_at=customer.created_at,
            )
        )
        await self._session.flush()

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        row = await self._session.get(CustomerRow, customer_id)
        return _to_customer(row) if row is not None else None

    async def get_by_keycloak_sub(self, keycloak_sub: str) -> Customer | None:
        row = await self._session.scalar(
            select(CustomerRow).where(CustomerRow.keycloak_sub == keycloak_sub)
        )
        return _to_customer(row) if row is not None else None

    async def get_by_email(self, email: str) -> Customer | None:
        row = await self._session.scalar(select(CustomerRow).where(CustomerRow.email == email))
        return _to_customer(row) if row is not None else None

    async def update_email(self, customer_id: UUID, email: str) -> None:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return
        row.email = email
        await self._session.flush()


def _to_customer(row: CustomerRow) -> Customer:
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return Customer(
        id=row.id,
        keycloak_sub=row.keycloak_sub,
        email=row.email,
        created_at=created_at,
    )
