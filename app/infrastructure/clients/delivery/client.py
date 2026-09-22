from typing import Protocol
from uuid import uuid4

from app.core.constants import DELIVERY_PROVIDER_STUB
from app.domain.models.delivery import DeliveryStatus
from app.infrastructure.clients.delivery.schemas import DispatchRequest, DispatchResponse


class DeliveryClient(Protocol):
    async def dispatch(self, request: DispatchRequest) -> DispatchResponse: ...


class StubDeliveryClient:
    async def dispatch(self, request: DispatchRequest) -> DispatchResponse:
        return DispatchResponse(
            provider=DELIVERY_PROVIDER_STUB,
            provider_reference=str(uuid4()),
            status=DeliveryStatus.DELIVERED,
        )
