from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.cart import CartOwner, session_cart_key
from app.infrastructure.clients.delivery.client import DeliveryClient, StubDeliveryClient
from app.infrastructure.clients.payment.client import PaymentClient, StubPaymentClient
from app.repositories.cart_repository import CartRepository, InMemoryCartRepository
from app.repositories.delivery_repository import SqlDeliveryRepository
from app.repositories.order_repository import SqlOrderRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.payment_repository import SqlPaymentRepository
from app.repositories.product_repository import InMemoryProductRepository
from app.services.cart_service import CartService
from app.services.delivery_service import DeliveryService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

TEST_SESSION_ID = "test-session"
TEST_OWNER_KEY = session_cart_key(TEST_SESSION_ID)
TEST_CART_OWNER = CartOwner(key=TEST_OWNER_KEY, session_id=TEST_SESSION_ID)


def make_commerce_services(
    session: AsyncSession,
    *,
    payment_client: PaymentClient | None = None,
    delivery_client: DeliveryClient | None = None,
    cart_repository: CartRepository | None = None,
) -> tuple[CartService, OrderService, PaymentService, DeliveryService]:
    products = InMemoryProductRepository.with_seed_data()
    orders = SqlOrderRepository(session)
    outbox = SqlOutboxRepository(session)
    order_service = OrderService(order_repository=orders, outbox_repository=outbox)
    cart_service = CartService(
        cart_repository=cart_repository or InMemoryCartRepository(),
        product_repository=products,
        order_service=order_service,
    )
    payment_service = PaymentService(
        order_repository=orders,
        payment_repository=SqlPaymentRepository(session),
        outbox_repository=outbox,
        order_service=order_service,
        payment_client=payment_client or StubPaymentClient(),
    )
    delivery_service = DeliveryService(
        order_repository=orders,
        delivery_repository=SqlDeliveryRepository(session),
        outbox_repository=outbox,
        order_service=order_service,
        delivery_client=delivery_client or StubDeliveryClient(),
    )
    return cart_service, order_service, payment_service, delivery_service
