from app.core.constants import PAYMENT_PROVIDER_STUB
from app.infrastructure.clients.payment.schemas import ChargeRequest, ChargeResponse


class FailingPaymentClient:
    async def charge(self, request: ChargeRequest) -> ChargeResponse:
        return ChargeResponse(
            succeeded=False,
            provider=PAYMENT_PROVIDER_STUB,
            provider_reference=None,
            failure_reason="declined",
        )
