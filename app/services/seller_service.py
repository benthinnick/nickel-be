from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.constants import (
    DEFAULT_CURRENCY,
    PRODUCT_CREATED_EVENT,
    PRODUCTS_TOPIC,
)
from app.core.exceptions import (
    AlreadySellerMemberError,
    CannotRemoveLastOwnerError,
    ForbiddenError,
    InsufficientStockError,
    ProductNotFoundError,
    SellerNotFoundError,
    SkuAlreadyTakenError,
    UserNotFoundError,
)
from app.domain.models.product import Product, ProductStatus
from app.domain.models.seller import Seller, SellerMembership, SellerRole
from app.domain.models.user import User
from app.infrastructure.kafka.schemas.events import EventEnvelope, ProductCreatedPayload
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.seller_repository import SellerRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class ProductCreateAccepted:
    product_id: UUID
    event_id: UUID
    event: EventEnvelope


class SellerService:
    def __init__(
        self,
        seller_repository: SellerRepository,
        user_repository: UserRepository,
        product_repository: ProductRepository,
        outbox_repository: OutboxRepository,
    ) -> None:
        self._sellers = seller_repository
        self._users = user_repository
        self._products = product_repository
        self._outbox = outbox_repository

    async def create_seller(self, *, name: str, owner: User) -> Seller:
        now = datetime.now(UTC)
        seller = Seller(id=uuid4(), name=name.strip(), created_at=now)
        await self._sellers.add(seller)
        await self._sellers.add_membership(
            SellerMembership(
                seller_id=seller.id,
                user_id=owner.id,
                role=SellerRole.OWNER,
                created_at=now,
            )
        )
        return seller

    async def list_for_user(self, user_id: UUID) -> list[tuple[Seller, SellerRole]]:
        return await self._sellers.list_for_user(user_id)

    async def get_for_member(self, seller_id: UUID, user: User) -> Seller:
        await self.require_member(seller_id, user)
        seller = await self._sellers.get_by_id(seller_id)
        if seller is None:
            raise SellerNotFoundError(seller_id)
        return seller

    async def list_memberships(self, seller_id: UUID, user: User) -> list[SellerMembership]:
        await self.require_member(seller_id, user)
        return await self._sellers.list_memberships(seller_id)

    async def invite_member(self, seller_id: UUID, *, owner: User, email: str) -> SellerMembership:
        await self.require_owner(seller_id, owner)
        invitee = await self._users.get_by_email(email.strip().lower())
        if invitee is None:
            raise UserNotFoundError(email)
        existing = await self._sellers.get_membership(seller_id, invitee.id)
        if existing is not None:
            raise AlreadySellerMemberError(invitee.id)
        membership = SellerMembership(
            seller_id=seller_id,
            user_id=invitee.id,
            role=SellerRole.MEMBER,
            created_at=datetime.now(UTC),
        )
        await self._sellers.add_membership(membership)
        return membership

    async def remove_member(self, seller_id: UUID, *, owner: User, user_id: UUID) -> None:
        await self.require_owner(seller_id, owner)
        membership = await self._sellers.get_membership(seller_id, user_id)
        if membership is None:
            return
        if membership.role == SellerRole.OWNER:
            owners = await self._sellers.count_owners(seller_id)
            if owners <= 1:
                raise CannotRemoveLastOwnerError(seller_id)
        await self._sellers.remove_membership(seller_id, user_id)

    async def list_products(
        self,
        seller_id: UUID,
        user: User,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        await self.require_member(seller_id, user)
        return await self._products.list_by_seller(seller_id, limit=limit, offset=offset)

    async def request_product_create(
        self,
        seller_id: UUID,
        user: User,
        *,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        currency: str = DEFAULT_CURRENCY,
        stock: int,
        image_url: str | None = None,
    ) -> ProductCreateAccepted:
        await self.require_member(seller_id, user)
        existing = await self._products.get_by_seller_and_sku(seller_id, sku)
        if existing is not None:
            raise SkuAlreadyTakenError(sku)
        product_id = uuid4()
        payload = ProductCreatedPayload(
            product_id=product_id,
            seller_id=seller_id,
            sku=sku,
            name=name,
            description=description,
            price=price,
            currency=currency,
            stock=stock,
            image_url=image_url,
            created_by_user_id=user.id,
        ).model_dump(mode="json")
        occurred_at = datetime.now(UTC)
        event_id = await self._outbox.enqueue(
            event_type=PRODUCT_CREATED_EVENT,
            aggregate_id=product_id,
            payload=payload,
            topic=PRODUCTS_TOPIC,
        )
        event = EventEnvelope(
            event_id=event_id,
            event_type=PRODUCT_CREATED_EVENT,
            occurred_at=occurred_at,
            payload=payload,
        )
        return ProductCreateAccepted(product_id=product_id, event_id=event_id, event=event)

    async def adjust_stock(
        self,
        seller_id: UUID,
        product_id: UUID,
        user: User,
        *,
        delta: int,
    ) -> Product:
        product = await self._seller_product(seller_id, product_id, user)
        next_stock = product.stock + delta
        if next_stock < 0:
            raise InsufficientStockError(product.id, product.stock)
        updated = Product(
            id=product.id,
            seller_id=product.seller_id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            price=product.price,
            currency=product.currency,
            status=product.status,
            stock=next_stock,
            image_url=product.image_url,
        )
        await self._products.save(updated)
        return updated

    async def hide_product(self, seller_id: UUID, product_id: UUID, user: User) -> Product:
        return await self._set_status(seller_id, product_id, user, ProductStatus.INACTIVE)

    async def unhide_product(self, seller_id: UUID, product_id: UUID, user: User) -> Product:
        return await self._set_status(seller_id, product_id, user, ProductStatus.ACTIVE)

    async def require_member(self, seller_id: UUID, user: User) -> SellerMembership:
        seller = await self._sellers.get_by_id(seller_id)
        if seller is None:
            raise SellerNotFoundError(seller_id)
        membership = await self._sellers.get_membership(seller_id, user.id)
        if membership is None:
            raise ForbiddenError("You are not a member of this seller")
        return membership

    async def require_owner(self, seller_id: UUID, user: User) -> SellerMembership:
        membership = await self.require_member(seller_id, user)
        if membership.role != SellerRole.OWNER:
            raise ForbiddenError("Only a seller owner can perform this action")
        return membership

    async def _seller_product(self, seller_id: UUID, product_id: UUID, user: User) -> Product:
        await self.require_member(seller_id, user)
        product = await self._products.get_by_id(product_id)
        if product is None or product.seller_id != seller_id:
            raise ProductNotFoundError(product_id)
        return product

    async def _set_status(
        self,
        seller_id: UUID,
        product_id: UUID,
        user: User,
        status: ProductStatus,
    ) -> Product:
        product = await self._seller_product(seller_id, product_id, user)
        updated = Product(
            id=product.id,
            seller_id=product.seller_id,
            sku=product.sku,
            name=product.name,
            description=product.description,
            price=product.price,
            currency=product.currency,
            status=status,
            stock=product.stock,
            image_url=product.image_url,
        )
        await self._products.save(updated)
        return updated
