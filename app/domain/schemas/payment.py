from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.models.payment import Payment, PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    status: PaymentStatus
    provider: str
    provider_reference: str | None
    amount: Decimal
    currency: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


def payment_to_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        status=payment.status,
        provider=payment.provider,
        provider_reference=payment.provider_reference,
        amount=payment.amount,
        currency=payment.currency,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )
