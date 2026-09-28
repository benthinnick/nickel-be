from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.constants import (
    DEFAULT_CURRENCY,
    PRODUCT_CREATED_EVENT,
    PRODUCT_HIDDEN_EVENT,
    PRODUCT_UNHIDDEN_EVENT,
    PRODUCTS_TOPIC,
)
from app.core.exceptions import (
    AlreadySellerMemberError,
    CannotRemoveLastOwnerError,
    CustomerNotFoundError,
    ForbiddenError,
    InsufficientStockError,
    ProductNotFoundError,
    SellerNotFoundError,
    SkuAlreadyTakenError,
)
from app.domain.models.customer import Customer
from app.domain.models.product import Product, ProductStatus
from app.domain.models.seller import Seller, SellerMembership, SellerRole
from app.infrastructure.clients.keycloak.client import KeycloakAdmin
from app.infrastructure.kafka.schemas.events import (
    EventEnvelope,
    ProductCreatedPayload,
    ProductVisibilityPayload,
)
from app.infrastructure.sanitization.html import sanitize_product_fields
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.seller_repository import SellerRepository
from app.services.customer_service import CustomerService


@dataclass(frozen=True)
class ProductCreateAccepted:
    product_id: UUID
    event_id: UUID
    event: EventEnvelope


@dataclass(frozen=True)
class ProductMutationAccepted:
    product: Product
    event: EventEnvelope


class SellerService:
    def __init__(
        self,
        seller_repository: SellerRepository,
        customer_service: CustomerService,
        keycloak_admin: KeycloakAdmin,
        product_repository: ProductRepository,
        outbox_repository: OutboxRepository,
    ) -> None:
        self._sellers = seller_repository
        self._customers = customer_service
        self._keycloak = keycloak_admin
        self._products = product_repository
        self._outbox = outbox_repository

    async def create_seller(self, *, name: str, owner: Customer) -> Seller:
        now = datetime.now(UTC)
        seller = Seller(id=uuid4(), name=name.strip(), created_at=now)
        await self._sellers.add(seller)
        await self._sellers.add_membership(
            SellerMembership(
                seller_id=seller.id,
                customer_id=owner.id,
                role=SellerRole.OWNER,
                created_at=now,
            )
        )
        return seller

    async def list_for_customer(self, customer_id: UUID) -> list[tuple[Seller, SellerRole]]:
        return await self._sellers.list_for_customer(customer_id)

    async def get_for_member(self, seller_id: UUID, customer: Customer) -> Seller:
        await self.require_member(seller_id, customer)
        seller = await self._sellers.get_by_id(seller_id)
        if seller is None:
            raise SellerNotFoundError(seller_id)
        return seller

    async def list_memberships(self, seller_id: UUID, customer: Customer) -> list[SellerMembership]:
        await self.require_member(seller_id, customer)
        return await self._sellers.list_memberships(seller_id)

    async def invite_member(
        self, seller_id: UUID, *, owner: Customer, email: str
    ) -> SellerMembership:
        await self.require_owner(seller_id, owner)
        invitee = await self._resolve_invitee(email)
        existing = await self._sellers.get_membership(seller_id, invitee.id)
        if existing is not None:
            raise AlreadySellerMemberError(invitee.id)
        membership = SellerMembership(
            seller_id=seller_id,
            customer_id=invitee.id,
            role=SellerRole.MEMBER,
            created_at=datetime.now(UTC),
        )
        await self._sellers.add_membership(membership)
        return membership

    async def remove_member(self, seller_id: UUID, *, owner: Customer, customer_id: UUID) -> None:
        await self.require_owner(seller_id, owner)
        membership = await self._sellers.get_membership(seller_id, customer_id)
        if membership is None:
            return
        if membership.role == SellerRole.OWNER:
            owners = await self._sellers.count_owners(seller_id)
            if owners <= 1:
                raise CannotRemoveLastOwnerError(seller_id)
        await self._sellers.remove_membership(seller_id, customer_id)

    async def list_products(
        self,
        seller_id: UUID,
        customer: Customer,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        await self.require_member(seller_id, customer)
        return await self._products.list_by_seller(seller_id, limit=limit, offset=offset)

    async def request_product_create(
        self,
        seller_id: UUID,
        customer: Customer,
        *,
        sku: str,
        name: str,
        description: str,
        price: Decimal,
        currency: str = DEFAULT_CURRENCY,
        stock: int,
        image_url: str | None = None,
    ) -> ProductCreateAccepted:
        await self.require_member(seller_id, customer)
        sku, name, description, image_url = sanitize_product_fields(
            sku=sku,
            name=name,
            description=description,
            image_url=image_url,
        )
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
            created_by_customer_id=customer.id,
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
        customer: Customer,
        *,
        delta: int,
    ) -> Product:
        product = await self._seller_product(seller_id, product_id, customer)
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

    async def hide_product(
        self,
        seller_id: UUID,
        product_id: UUID,
        customer: Customer,
    ) -> ProductMutationAccepted:
        product = await self._set_status(seller_id, product_id, customer, ProductStatus.INACTIVE)
        event = await self._enqueue_visibility(product, PRODUCT_HIDDEN_EVENT)
        return ProductMutationAccepted(product=product, event=event)

    async def unhide_product(
        self,
        seller_id: UUID,
        product_id: UUID,
        customer: Customer,
    ) -> ProductMutationAccepted:
        product = await self._set_status(seller_id, product_id, customer, ProductStatus.ACTIVE)
        event = await self._enqueue_visibility(product, PRODUCT_UNHIDDEN_EVENT)
        return ProductMutationAccepted(product=product, event=event)

    async def require_member(self, seller_id: UUID, customer: Customer) -> SellerMembership:
        seller = await self._sellers.get_by_id(seller_id)
        if seller is None:
            raise SellerNotFoundError(seller_id)
        membership = await self._sellers.get_membership(seller_id, customer.id)
        if membership is None:
            raise ForbiddenError("You are not a member of this seller")
        return membership

    async def require_owner(self, seller_id: UUID, customer: Customer) -> SellerMembership:
        membership = await self.require_member(seller_id, customer)
        if membership.role != SellerRole.OWNER:
            raise ForbiddenError("Only a seller owner can perform this action")
        return membership

    async def _resolve_invitee(self, email: str) -> Customer:
        normalized = email.strip().lower()
        invitee = await self._customers.get_by_email(normalized)
        if invitee is not None:
            return invitee
        remote = await self._keycloak.find_user_by_email(normalized)
        if remote is None:
            raise CustomerNotFoundError(normalized)
        return await self._customers.ensure_from_identity(
            subject=remote.subject,
            email=remote.email,
        )

    async def _seller_product(
        self, seller_id: UUID, product_id: UUID, customer: Customer
    ) -> Product:
        await self.require_member(seller_id, customer)
        product = await self._products.get_by_id(product_id)
        if product is None or product.seller_id != seller_id:
            raise ProductNotFoundError(product_id)
        return product

    async def _set_status(
        self,
        seller_id: UUID,
        product_id: UUID,
        customer: Customer,
        status: ProductStatus,
    ) -> Product:
        product = await self._seller_product(seller_id, product_id, customer)
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

    async def _enqueue_visibility(self, product: Product, event_type: str) -> EventEnvelope:
        payload = ProductVisibilityPayload(
            product_id=product.id,
            seller_id=product.seller_id,
        ).model_dump(mode="json")
        occurred_at = datetime.now(UTC)
        event_id = await self._outbox.enqueue(
            event_type=event_type,
            aggregate_id=product.id,
            payload=payload,
            topic=PRODUCTS_TOPIC,
        )
        return EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            payload=payload,
        )
