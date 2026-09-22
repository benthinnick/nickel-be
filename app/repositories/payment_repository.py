from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.payment import Payment, PaymentStatus
from app.infrastructure.database.tables import PaymentRow


class PaymentRepository(Protocol):
    async def add(self, payment: Payment) -> None: ...

    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...

    async def get_by_order_id(self, order_id: UUID) -> Payment | None: ...

    async def save(self, payment: Payment) -> None: ...


class SqlPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, payment: Payment) -> None:
        self._session.add(_to_row(payment))
        await self._session.flush()

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        row = await self._session.get(PaymentRow, payment_id)
        return _to_payment(row) if row is not None else None

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        row = await self._session.scalar(select(PaymentRow).where(PaymentRow.order_id == order_id))
        return _to_payment(row) if row is not None else None

    async def save(self, payment: Payment) -> None:
        row = await self._session.get(PaymentRow, payment.id)
        if row is None:
            await self.add(payment)
            return
        row.status = payment.status.value
        row.provider = payment.provider
        row.provider_reference = payment.provider_reference
        row.failure_reason = payment.failure_reason
        row.updated_at = payment.updated_at
        await self._session.flush()


def _to_row(payment: Payment) -> PaymentRow:
    return PaymentRow(
        id=payment.id,
        order_id=payment.order_id,
        status=payment.status.value,
        provider=payment.provider,
        provider_reference=payment.provider_reference,
        amount=payment.amount,
        currency=payment.currency,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


def _to_payment(row: PaymentRow) -> Payment:
    return Payment(
        id=row.id,
        order_id=row.order_id,
        status=PaymentStatus(row.status),
        provider=row.provider,
        provider_reference=row.provider_reference,
        amount=Decimal(row.amount),
        currency=row.currency,
        failure_reason=row.failure_reason,
        created_at=_ensure_utc(row.created_at),
        updated_at=_ensure_utc(row.updated_at),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
