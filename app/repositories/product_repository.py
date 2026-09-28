from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_CURRENCY, DEFAULT_SEED_STOCK
from app.domain.models.product import Product, ProductStatus
from app.infrastructure.database.tables import ProductRow, SellerRow

COFFEE_ID = UUID("11111111-1111-4111-8111-111111111111")
TEA_ID = UUID("22222222-2222-4222-8222-222222222222")
HONEY_ID = UUID("33333333-3333-4333-8333-333333333333")
ARCHIVED_ID = UUID("44444444-4444-4444-8444-444444444444")
DEMO_SELLER_ID = UUID("55555555-5555-4555-8555-555555555555")


def seed_products() -> list[Product]:
    return [
        Product(
            id=COFFEE_ID,
            seller_id=DEMO_SELLER_ID,
            sku="SKU-COFFEE-250",
            name="Ethiopian Coffee Beans",
            description="250g of medium-roast Ethiopian coffee beans.",
            price=Decimal("42.90"),
            currency=DEFAULT_CURRENCY,
            status=ProductStatus.ACTIVE,
            stock=DEFAULT_SEED_STOCK,
            image_url=None,
        ),
        Product(
            id=TEA_ID,
            seller_id=DEMO_SELLER_ID,
            sku="SKU-TEA-100",
            name="Earl Grey Tea",
            description="100g loose-leaf Earl Grey tea.",
            price=Decimal("24.50"),
            currency=DEFAULT_CURRENCY,
            status=ProductStatus.ACTIVE,
            stock=DEFAULT_SEED_STOCK,
            image_url=None,
        ),
        Product(
            id=HONEY_ID,
            seller_id=DEMO_SELLER_ID,
            sku="SKU-HONEY-500",
            name="Wildflower Honey",
            description="500g jar of wildflower honey.",
            price=Decimal("36.00"),
            currency=DEFAULT_CURRENCY,
            status=ProductStatus.ACTIVE,
            stock=DEFAULT_SEED_STOCK,
            image_url=None,
        ),
        Product(
            id=ARCHIVED_ID,
            seller_id=DEMO_SELLER_ID,
            sku="SKU-ARCHIVED-001",
            name="Discontinued Spice Mix",
            description="No longer sold.",
            price=Decimal("12.00"),
            currency=DEFAULT_CURRENCY,
            status=ProductStatus.INACTIVE,
            stock=0,
            image_url=None,
        ),
    ]


class ProductRepository(Protocol):
    async def list_active(self, *, limit: int, offset: int) -> tuple[list[Product], int]: ...

    async def list_by_seller(
        self,
        seller_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]: ...

    async def get_by_id(self, product_id: UUID) -> Product | None: ...

    async def get_by_seller_and_sku(self, seller_id: UUID, sku: str) -> Product | None: ...

    async def add(self, product: Product) -> None: ...

    async def save(self, product: Product) -> None: ...


class InMemoryProductRepository:
    def __init__(self, products: list[Product] | None = None) -> None:
        seeded = products if products is not None else seed_products()
        self._products = {product.id: product for product in seeded}

    @classmethod
    def with_seed_data(cls) -> "InMemoryProductRepository":
        return cls(seed_products())

    async def list_active(self, *, limit: int, offset: int) -> tuple[list[Product], int]:
        active = [
            product for product in self._products.values() if product.status == ProductStatus.ACTIVE
        ]
        active.sort(key=lambda product: product.name)
        return active[offset : offset + limit], len(active)

    async def list_by_seller(
        self,
        seller_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        items = [product for product in self._products.values() if product.seller_id == seller_id]
        items.sort(key=lambda product: product.name)
        return items[offset : offset + limit], len(items)

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return self._products.get(product_id)

    async def get_by_seller_and_sku(self, seller_id: UUID, sku: str) -> Product | None:
        for product in self._products.values():
            if product.seller_id == seller_id and product.sku == sku:
                return product
        return None

    async def add(self, product: Product) -> None:
        self._products[product.id] = product

    async def save(self, product: Product) -> None:
        self._products[product.id] = product


class SqlProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, *, limit: int, offset: int) -> tuple[list[Product], int]:
        filters = ProductRow.status == ProductStatus.ACTIVE.value
        total = await self._session.scalar(
            select(func.count()).select_from(ProductRow).where(filters)
        )
        result = await self._session.scalars(
            select(ProductRow).where(filters).order_by(ProductRow.name).offset(offset).limit(limit)
        )
        return [_to_product(row) for row in result.all()], int(total or 0)

    async def list_by_seller(
        self,
        seller_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        filters = ProductRow.seller_id == seller_id
        total = await self._session.scalar(
            select(func.count()).select_from(ProductRow).where(filters)
        )
        result = await self._session.scalars(
            select(ProductRow).where(filters).order_by(ProductRow.name).offset(offset).limit(limit)
        )
        return [_to_product(row) for row in result.all()], int(total or 0)

    async def get_by_id(self, product_id: UUID) -> Product | None:
        row = await self._session.get(ProductRow, product_id)
        return _to_product(row) if row is not None else None

    async def get_by_seller_and_sku(self, seller_id: UUID, sku: str) -> Product | None:
        row = await self._session.scalar(
            select(ProductRow).where(ProductRow.seller_id == seller_id, ProductRow.sku == sku)
        )
        return _to_product(row) if row is not None else None

    async def add(self, product: Product) -> None:
        self._session.add(_to_row(product))
        await self._session.flush()

    async def save(self, product: Product) -> None:
        row = await self._session.get(ProductRow, product.id)
        if row is None:
            await self.add(product)
            return
        row.seller_id = product.seller_id
        row.sku = product.sku
        row.name = product.name
        row.description = product.description
        row.price = product.price
        row.currency = product.currency
        row.status = product.status.value
        row.stock = product.stock
        row.image_url = product.image_url
        await self._session.flush()


async def seed_demo_catalog(session: AsyncSession) -> None:
    existing = await session.get(ProductRow, COFFEE_ID)
    if existing is not None:
        return
    now = datetime.now(UTC)
    if await session.get(SellerRow, DEMO_SELLER_ID) is None:
        session.add(SellerRow(id=DEMO_SELLER_ID, name="Demo Seller", created_at=now))
    for product in seed_products():
        if await session.get(ProductRow, product.id) is None:
            session.add(_to_row(product))
    await session.flush()


def _to_row(product: Product) -> ProductRow:
    return ProductRow(
        id=product.id,
        seller_id=product.seller_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        price=product.price,
        currency=product.currency,
        status=product.status.value,
        stock=product.stock,
        image_url=product.image_url,
    )


def _to_product(row: ProductRow) -> Product:
    return Product(
        id=row.id,
        seller_id=row.seller_id,
        sku=row.sku,
        name=row.name,
        description=row.description,
        price=Decimal(row.price),
        currency=row.currency,
        status=ProductStatus(row.status),
        stock=row.stock,
        image_url=row.image_url,
    )
