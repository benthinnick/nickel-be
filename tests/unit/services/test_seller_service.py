from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CannotRemoveLastOwnerError,
    CustomerNotFoundError,
    ForbiddenError,
    InsufficientStockError,
    InvalidProductError,
)
from app.domain.models.product import ProductStatus
from app.infrastructure.clients.keycloak.client import InMemoryKeycloakAdmin
from app.infrastructure.kafka.schemas.events import ProductCreatedPayload
from app.repositories.customer_repository import SqlCustomerRepository
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.product_repository import SqlProductRepository
from app.repositories.seller_repository import SqlSellerRepository
from app.services.customer_service import CustomerService
from app.services.product_service import ProductService
from app.services.seller_service import SellerService


def _services(db_session) -> tuple[CustomerService, SellerService, ProductService]:
    products = SqlProductRepository(db_session)
    customers = CustomerService(SqlCustomerRepository(db_session))
    return (
        customers,
        SellerService(
            seller_repository=SqlSellerRepository(db_session),
            customer_service=customers,
            keycloak_admin=InMemoryKeycloakAdmin(),
            product_repository=products,
            outbox_repository=SqlOutboxRepository(db_session),
        ),
        ProductService(products),
    )


async def _customer(customers: CustomerService, email: str):
    return await customers.ensure_from_identity(subject=str(uuid4()), email=email)


async def _owner_and_seller(db_session):
    customers, sellers, products = _services(db_session)
    owner = await _customer(customers, "owner@example.com")
    seller = await sellers.create_seller(name="Ada Market", owner=owner)
    return customers, sellers, products, owner, seller


async def _create_catalog_product(sellers, products, seller, owner):
    accepted = await sellers.request_product_create(
        seller.id,
        owner,
        sku="SKU-NEW",
        name="New Spice",
        description="Fresh",
        price=Decimal("10.00"),
        stock=5,
    )
    payload = ProductCreatedPayload.model_validate(accepted.event.payload)
    return await products.apply_created(payload)


async def test_non_member_cannot_mutate_seller_products(db_session) -> None:
    customers, sellers, products, owner, seller = await _owner_and_seller(db_session)
    outsider = await _customer(customers, "outsider@example.com")
    product = await _create_catalog_product(sellers, products, seller, owner)

    with pytest.raises(ForbiddenError):
        await sellers.adjust_stock(seller.id, product.id, outsider, delta=1)
    with pytest.raises(ForbiddenError):
        await sellers.hide_product(seller.id, product.id, outsider)


async def test_member_can_adjust_stock_and_hide(db_session) -> None:
    customers, sellers, products, owner, seller = await _owner_and_seller(db_session)
    member = await _customer(customers, "member@example.com")
    await sellers.invite_member(seller.id, owner=owner, email=member.email)
    product = await _create_catalog_product(sellers, products, seller, owner)

    updated = await sellers.adjust_stock(seller.id, product.id, member, delta=3)
    hidden = await sellers.hide_product(seller.id, product.id, member)

    assert updated.stock == 8
    assert hidden.product.status == ProductStatus.INACTIVE


async def test_member_cannot_invite(db_session) -> None:
    customers, sellers, _, owner, seller = await _owner_and_seller(db_session)
    member = await _customer(customers, "member@example.com")
    await sellers.invite_member(seller.id, owner=owner, email=member.email)
    other = await _customer(customers, "other@example.com")

    with pytest.raises(ForbiddenError):
        await sellers.invite_member(seller.id, owner=member, email=other.email)


async def test_cannot_remove_last_owner(db_session) -> None:
    _, sellers, _, owner, seller = await _owner_and_seller(db_session)

    with pytest.raises(CannotRemoveLastOwnerError):
        await sellers.remove_member(seller.id, owner=owner, customer_id=owner.id)


async def test_invite_provisions_from_keycloak_when_customer_missing(db_session) -> None:
    customers, _, products = _services(db_session)
    admin = InMemoryKeycloakAdmin()
    admin.add_user(subject="kc-member", email="remote@example.com")
    sellers = SellerService(
        seller_repository=SqlSellerRepository(db_session),
        customer_service=customers,
        keycloak_admin=admin,
        product_repository=products,
        outbox_repository=SqlOutboxRepository(db_session),
    )
    owner = await _customer(customers, "owner@example.com")
    seller = await sellers.create_seller(name="Ada Market", owner=owner)

    membership = await sellers.invite_member(seller.id, owner=owner, email="remote@example.com")
    invitee = await customers.get_by_email("remote@example.com")

    assert invitee is not None
    assert invitee.keycloak_sub == "kc-member"
    assert membership.customer_id == invitee.id


async def test_invite_unknown_email_raises(db_session) -> None:
    _, sellers, _, owner, seller = await _owner_and_seller(db_session)

    with pytest.raises(CustomerNotFoundError):
        await sellers.invite_member(seller.id, owner=owner, email="missing@example.com")


async def test_stock_delta_cannot_go_negative(db_session) -> None:
    _, sellers, products, owner, seller = await _owner_and_seller(db_session)
    product = await _create_catalog_product(sellers, products, seller, owner)

    with pytest.raises(InsufficientStockError):
        await sellers.adjust_stock(seller.id, product.id, owner, delta=-6)


async def test_product_create_strips_xss_from_name(db_session) -> None:
    _, sellers, products, owner, seller = await _owner_and_seller(db_session)
    accepted = await sellers.request_product_create(
        seller.id,
        owner,
        sku="SKU-XSS",
        name="<script>alert(1)</script>Coffee",
        description="<b>Rich</b>",
        price=Decimal("10.00"),
        stock=5,
    )
    payload = ProductCreatedPayload.model_validate(accepted.event.payload)
    product = await products.apply_created(payload)

    assert "<" not in product.name
    assert "script" not in product.name.lower()
    assert "Coffee" in product.name
    assert "<" not in product.description


async def test_product_create_rejects_javascript_image_url(db_session) -> None:
    _, sellers, _, owner, seller = await _owner_and_seller(db_session)

    with pytest.raises(InvalidProductError) as exc:
        await sellers.request_product_create(
            seller.id,
            owner,
            sku="SKU-BAD-IMG",
            name="Coffee",
            description="Safe",
            price=Decimal("10.00"),
            stock=5,
            image_url="javascript:alert(1)",
        )

    assert exc.value.code == "invalid_product"
