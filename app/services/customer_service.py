from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository


class CustomerService:
    def __init__(self, customer_repository: CustomerRepository) -> None:
        self._customers = customer_repository

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        return await self._customers.get_by_id(customer_id)

    async def get_by_email(self, email: str) -> Customer | None:
        return await self._customers.get_by_email(_normalize_email(email))

    async def ensure_from_identity(self, *, subject: str, email: str) -> Customer:
        normalized = _normalize_email(email)
        existing = await self._customers.get_by_keycloak_sub(subject)
        if existing is None:
            customer = Customer(
                id=uuid4(),
                keycloak_sub=subject,
                email=normalized,
                created_at=datetime.now(UTC),
            )
            await self._customers.add(customer)
            return customer
        if existing.email != normalized:
            taken = await self._customers.get_by_email(normalized)
            if taken is None:
                await self._customers.update_email(existing.id, normalized)
                return replace(existing, email=normalized)
        return existing


def _normalize_email(email: str) -> str:
    return email.strip().lower()
