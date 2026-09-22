from typing import Protocol
from uuid import uuid4

from app.core.constants import PAYMENT_PROVIDER_STUB
from app.infrastructure.clients.payment.schemas import ChargeRequest, ChargeResponse


class PaymentClient(Protocol):
    async def charge(self, request: ChargeRequest) -> ChargeResponse: ...


class StubPaymentClient:
    async def charge(self, request: ChargeRequest) -> ChargeResponse:
        return ChargeResponse(
            succeeded=True,
            provider=PAYMENT_PROVIDER_STUB,
            provider_reference=str(uuid4()),
        )
