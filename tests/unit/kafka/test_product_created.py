from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.core.constants import PRODUCT_CREATED_EVENT
from app.infrastructure.kafka.handlers.product_created import create_handler
from app.infrastructure.kafka.schemas.events import EventEnvelope
from app.repositories.product_repository import (
    DEMO_SELLER_ID,
    SqlProductRepository,
    seed_demo_catalog,
)
from app.services.product_service import ProductService


async def test_product_created_handler_inserts_and_is_idempotent(session_factory) -> None:
    async with session_factory() as session:
        await seed_demo_catalog(session)
        await session.commit()

    product_id = uuid4()
    event = EventEnvelope(
        event_id=uuid4(),
        event_type=PRODUCT_CREATED_EVENT,
        occurred_at=datetime.now(UTC),
        payload={
            "product_id": str(product_id),
            "seller_id": str(DEMO_SELLER_ID),
            "sku": "SKU-KAFKA-1",
            "name": "Kafka Spice",
            "description": "Created by event",
            "price": "18.50",
            "currency": "ILS",
            "stock": 7,
            "image_url": None,
            "created_by_user_id": str(uuid4()),
        },
    )
    handler = create_handler(session_factory)
    await handler(event)
    await handler(event)

    async with session_factory() as session:
        product = await ProductService(SqlProductRepository(session)).get_product(product_id)
        assert product.name == "Kafka Spice"
        assert product.stock == 7
        assert product.seller_id == DEMO_SELLER_ID
        assert product.price == Decimal("18.50")
