from typing import Annotated

from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session import peek_session_id, resolve_session_id
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.domain.models.cart import CartOwner, customer_cart_key, session_cart_key
from app.domain.models.customer import Customer
from app.infrastructure.auth.oidc import TokenVerifier
from app.infrastructure.clients.delivery.client import DeliveryClient, StubDeliveryClient
from app.infrastructure.clients.keycloak.client import KeycloakAdmin
from app.infrastructure.clients.payment.client import PaymentClient, StubPaymentClient
from app.infrastructure.clients.search.client import SearchIndex
from app.infrastructure.database.session import get_db_session
from app.repositories.cart_repository import CartRepository, RedisCartRepository
from app.repositories.customer_repository import SqlCustomerRepository
from app.repositories.delivery_repository import SqlDeliveryRepository
from app.repositories.order_repository import SqlOrderRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.payment_repository import SqlPaymentRepository
from app.repositories.product_repository import ProductRepository, SqlProductRepository
from app.repositories.seller_repository import SqlSellerRepository
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService
from app.services.delivery_service import DeliveryService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService
from app.services.search_service import SearchService
from app.services.seller_service import SellerService

bearer_scheme = HTTPBearer(auto_error=False)


def get_product_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductRepository:
    return SqlProductRepository(session)


def get_product_service(
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductService:
    return ProductService(repository=repository)


def get_search_index(request: Request) -> SearchIndex:
    return request.app.state.search_index


def get_search_service(
    search_index: Annotated[SearchIndex, Depends(get_search_index)],
) -> SearchService:
    return SearchService(search_index)


def get_payment_client() -> PaymentClient:
    return StubPaymentClient()


def get_delivery_client() -> DeliveryClient:
    return StubDeliveryClient()


def get_session_id(request: Request, response: Response) -> str:
    return resolve_session_id(request, response)


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_cart_repository(
    redis: Annotated[Redis, Depends(get_redis)],
) -> CartRepository:
    settings = get_settings()
    return RedisCartRepository(redis, ttl_seconds=settings.session_ttl_seconds)


def get_order_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderService:
    return OrderService(
        order_repository=SqlOrderRepository(session),
        outbox_repository=SqlOutboxRepository(session),
    )


def get_customer_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerService:
    return CustomerService(customer_repository=SqlCustomerRepository(session))


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


def get_keycloak_admin(request: Request) -> KeycloakAdmin:
    return request.app.state.keycloak_admin


def get_seller_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    keycloak_admin: Annotated[KeycloakAdmin, Depends(get_keycloak_admin)],
) -> SellerService:
    return SellerService(
        seller_repository=SqlSellerRepository(session),
        customer_service=CustomerService(customer_repository=SqlCustomerRepository(session)),
        keycloak_admin=keycloak_admin,
        product_repository=SqlProductRepository(session),
        outbox_repository=SqlOutboxRepository(session),
    )


def get_cart_service(
    cart_repository: Annotated[CartRepository, Depends(get_cart_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
) -> CartService:
    return CartService(
        cart_repository=cart_repository,
        product_repository=products,
        order_service=order_service,
    )


async def get_current_customer_optional(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    customers: Annotated[CustomerService, Depends(get_customer_service)],
    carts: Annotated[CartService, Depends(get_cart_service)],
) -> Customer | None:
    if credentials is None:
        if request.headers.get("Authorization"):
            raise UnauthorizedError("Invalid or expired token")
        return None
    claims = await verifier.decode(credentials.credentials)
    customer = await customers.ensure_from_identity(subject=claims.subject, email=claims.email)
    session_id = peek_session_id(request)
    if session_id is not None:
        await carts.merge_session_into_customer(
            session_id=session_id,
            customer_id=customer.id,
        )
    return customer


async def get_current_customer(
    customer: Annotated[Customer | None, Depends(get_current_customer_optional)],
) -> Customer:
    if customer is None:
        raise UnauthorizedError()
    return customer


def get_cart_owner(
    session_id: Annotated[str, Depends(get_session_id)],
    customer: Annotated[Customer | None, Depends(get_current_customer_optional)],
) -> CartOwner:
    if customer is not None:
        return CartOwner(
            key=customer_cart_key(customer.id),
            session_id=session_id,
            customer_id=customer.id,
        )
    return CartOwner(key=session_cart_key(session_id), session_id=session_id, customer_id=None)


def get_payment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
    payment_client: Annotated[PaymentClient, Depends(get_payment_client)],
) -> PaymentService:
    return PaymentService(
        order_repository=SqlOrderRepository(session),
        payment_repository=SqlPaymentRepository(session),
        outbox_repository=SqlOutboxRepository(session),
        order_service=order_service,
        payment_client=payment_client,
    )


def get_delivery_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
    delivery_client: Annotated[DeliveryClient, Depends(get_delivery_client)],
) -> DeliveryService:
    return DeliveryService(
        order_repository=SqlOrderRepository(session),
        delivery_repository=SqlDeliveryRepository(session),
        outbox_repository=SqlOutboxRepository(session),
        order_service=order_service,
        delivery_client=delivery_client,
    )
