from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.core.constants import PRODUCT_HIDDEN_EVENT, PRODUCT_UNHIDDEN_EVENT
from app.infrastructure.clients.search.client import InMemorySearchIndex
from app.infrastructure.kafka.handlers.product_hidden import create_handler as create_hidden_handler
from app.infrastructure.kafka.handlers.product_unhidden import (
    create_handler as create_unhidden_handler,
)
from app.infrastructure.kafka.schemas.events import EventEnvelope
from app.repositories.product_repository import COFFEE_ID, DEMO_SELLER_ID, seed_demo_catalog
from tests.fixtures.products import make_product


def _visibility_event(event_type: str) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        payload={"product_id": str(COFFEE_ID), "seller_id": str(DEMO_SELLER_ID)},
    )


async def test_hidden_handler_removes_product_from_index(session_factory) -> None:
    async with session_factory() as session:
        await seed_demo_catalog(session)
        await session.commit()
    index = InMemorySearchIndex()
    await index.index(replace(make_product(name="Ethiopian Coffee Beans"), id=COFFEE_ID))

    handler = create_hidden_handler(session_factory, index)
    event = _visibility_event(PRODUCT_HIDDEN_EVENT)
    await handler(event)
    await handler(event)

    hits, total = await index.search_by_name("Coffee", limit=10, offset=0)
    assert total == 0
    assert hits == []


async def test_unhidden_handler_reindexes_active_product(session_factory) -> None:
    async with session_factory() as session:
        await seed_demo_catalog(session)
        await session.commit()
    index = InMemorySearchIndex()
    handler = create_unhidden_handler(session_factory, index)
    event = _visibility_event(PRODUCT_UNHIDDEN_EVENT)
    await handler(event)
    await handler(event)

    hits, total = await index.search_by_name("Coffee", limit=10, offset=0)
    assert total == 1
    assert hits[0].id == COFFEE_ID
