from decimal import Decimal

import pytest

from app.core.exceptions import (
    CannotRemoveLastOwnerError,
    ForbiddenError,
    InsufficientStockError,
)
from app.domain.models.product import ProductStatus
from app.infrastructure.kafka.schemas.events import ProductCreatedPayload
from app.repositories.outbox_repository import SqlOutboxRepository
from app.repositories.product_repository import SqlProductRepository
from app.repositories.seller_repository import SqlSellerRepository
from app.repositories.user_repository import SqlUserRepository
from app.services.product_service import ProductService
from app.services.seller_service import SellerService
from app.services.user_service import UserService


def _services(db_session) -> tuple[UserService, SellerService, ProductService]:
    products = SqlProductRepository(db_session)
    return (
        UserService(user_repository=SqlUserRepository(db_session)),
        SellerService(
            seller_repository=SqlSellerRepository(db_session),
            user_repository=SqlUserRepository(db_session),
            product_repository=products,
            outbox_repository=SqlOutboxRepository(db_session),
        ),
        ProductService(products),
    )


async def _owner_and_seller(db_session):
    users, sellers, products = _services(db_session)
    owner = await users.register(email="owner@example.com", password="secret123")
    seller = await sellers.create_seller(name="Ada Market", owner=owner)
    return users, sellers, products, owner, seller


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
    users, sellers, products, owner, seller = await _owner_and_seller(db_session)
    outsider = await users.register(email="outsider@example.com", password="secret123")
    product = await _create_catalog_product(sellers, products, seller, owner)

    with pytest.raises(ForbiddenError):
        await sellers.adjust_stock(seller.id, product.id, outsider, delta=1)
    with pytest.raises(ForbiddenError):
        await sellers.hide_product(seller.id, product.id, outsider)


async def test_member_can_adjust_stock_and_hide(db_session) -> None:
    users, sellers, products, owner, seller = await _owner_and_seller(db_session)
    member = await users.register(email="member@example.com", password="secret123")
    await sellers.invite_member(seller.id, owner=owner, email=member.email)
    product = await _create_catalog_product(sellers, products, seller, owner)

    updated = await sellers.adjust_stock(seller.id, product.id, member, delta=3)
    hidden = await sellers.hide_product(seller.id, product.id, member)

    assert updated.stock == 8
    assert hidden.status == ProductStatus.INACTIVE


async def test_member_cannot_invite(db_session) -> None:
    users, sellers, _, owner, seller = await _owner_and_seller(db_session)
    member = await users.register(email="member@example.com", password="secret123")
    await sellers.invite_member(seller.id, owner=owner, email=member.email)
    other = await users.register(email="other@example.com", password="secret123")

    with pytest.raises(ForbiddenError):
        await sellers.invite_member(seller.id, owner=member, email=other.email)


async def test_cannot_remove_last_owner(db_session) -> None:
    _, sellers, _, owner, seller = await _owner_and_seller(db_session)

    with pytest.raises(CannotRemoveLastOwnerError):
        await sellers.remove_member(seller.id, owner=owner, user_id=owner.id)


async def test_stock_delta_cannot_go_negative(db_session) -> None:
    _, sellers, products, owner, seller = await _owner_and_seller(db_session)
    product = await _create_catalog_product(sellers, products, seller, owner)

    with pytest.raises(InsufficientStockError):
        await sellers.adjust_stock(seller.id, product.id, owner, delta=-6)
