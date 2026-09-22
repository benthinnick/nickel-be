from typing import Annotated

from fastapi import Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session import resolve_session_id
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.domain.models.cart import CartOwner, session_cart_key, user_cart_key
from app.domain.models.user import User
from app.infrastructure.auth.tokens import decode_access_token
from app.infrastructure.clients.delivery.client import DeliveryClient, StubDeliveryClient
from app.infrastructure.clients.payment.client import PaymentClient, StubPaymentClient
from app.infrastructure.database.session import get_db_session
from app.repositories.cart_repository import CartRepository, RedisCartRepository
from app.repositories.delivery_repository import SqlDeliveryRepository
from app.repositories.order_repository import SqlOrderRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.payment_repository import SqlPaymentRepository
from app.repositories.product_repository import ProductRepository, SqlProductRepository
from app.repositories.seller_repository import SqlSellerRepository
from app.repositories.user_repository import SqlUserRepository
from app.services.cart_service import CartService
from app.services.delivery_service import DeliveryService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_service import ProductService
from app.services.seller_service import SellerService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_product_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductRepository:
    return SqlProductRepository(session)


def get_product_service(
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductService:
    return ProductService(repository=repository)


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


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    return UserService(user_repository=SqlUserRepository(session))


def get_seller_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SellerService:
    return SellerService(
        seller_repository=SqlSellerRepository(session),
        user_repository=SqlUserRepository(session),
        product_repository=SqlProductRepository(session),
        outbox_repository=SqlOutboxRepository(session),
    )


async def get_current_user_optional(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    users: Annotated[UserService, Depends(get_user_service)],
) -> User | None:
    if token is None:
        if request.headers.get("Authorization"):
            raise UnauthorizedError("Invalid or expired token")
        return None
    claims = decode_access_token(token)
    return await users.get_by_id(claims.user_id)


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise UnauthorizedError()
    return user


def get_cart_owner(
    session_id: Annotated[str, Depends(get_session_id)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> CartOwner:
    if user is not None:
        return CartOwner(key=user_cart_key(user.id), session_id=session_id, user_id=user.id)
    return CartOwner(key=session_cart_key(session_id), session_id=session_id, user_id=None)


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
