from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.constants import ORDER_PAYMENT_FAILED_EVENT, ORDER_PAYMENT_SUCCEEDED_EVENT
from app.core.exceptions import OrderNotFoundError, OrderNotPayableError
from app.domain.models.order import OrderStatus
from app.domain.models.payment import Payment, PaymentStatus
from app.infrastructure.clients.payment.client import PaymentClient
from app.infrastructure.clients.payment.schemas import ChargeRequest
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.order_service import OrderService


class PaymentService:
    def __init__(
        self,
        order_repository: OrderRepository,
        payment_repository: PaymentRepository,
        outbox_repository: OutboxRepository,
        order_service: OrderService,
        payment_client: PaymentClient,
    ) -> None:
        self._orders = order_repository
        self._payments = payment_repository
        self._outbox = outbox_repository
        self._order_service = order_service
        self._payment_client = payment_client

    async def start_payment(self, order_id: UUID) -> Payment:
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)

        existing = await self._payments.get_by_order_id(order_id)
        if existing is not None:
            return existing

        if order.status != OrderStatus.PENDING_PAYMENT:
            raise OrderNotPayableError(order_id, order.status.value)

        payment_id = uuid4()
        now = datetime.now(UTC)
        charge = await self._payment_client.charge(
            ChargeRequest(
                payment_id=payment_id,
                order_id=order.id,
                amount=order.total,
                currency=order.currency,
            )
        )
        completed_at = datetime.now(UTC)
        if charge.succeeded:
            payment = Payment(
                id=payment_id,
                order_id=order.id,
                status=PaymentStatus.SUCCEEDED,
                provider=charge.provider,
                provider_reference=charge.provider_reference,
                amount=order.total,
                currency=order.currency,
                failure_reason=None,
                created_at=now,
                updated_at=completed_at,
            )
            await self._payments.add(payment)
            await self._order_service.mark_paid(order.id)
            await self._outbox.enqueue(
                event_type=ORDER_PAYMENT_SUCCEEDED_EVENT,
                aggregate_id=order.id,
                payload={
                    "order_id": str(order.id),
                    "payment_id": str(payment.id),
                    "total": str(order.total),
                    "currency": order.currency,
                },
            )
            return payment

        payment = Payment(
            id=payment_id,
            order_id=order.id,
            status=PaymentStatus.FAILED,
            provider=charge.provider,
            provider_reference=charge.provider_reference,
            amount=order.total,
            currency=order.currency,
            failure_reason=charge.failure_reason,
            created_at=now,
            updated_at=completed_at,
        )
        await self._payments.add(payment)
        await self._order_service.mark_payment_failed(order.id)
        await self._outbox.enqueue(
            event_type=ORDER_PAYMENT_FAILED_EVENT,
            aggregate_id=order.id,
            payload={
                "order_id": str(order.id),
                "payment_id": str(payment.id),
                "total": str(order.total),
                "currency": order.currency,
                "failure_reason": charge.failure_reason,
            },
        )
        return payment

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        return await self._payments.get_by_order_id(order_id)
