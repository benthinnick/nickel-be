from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import (
    ORDER_DELIVERED_EVENT,
    ORDER_PAYMENT_SUCCEEDED_EVENT,
    PRODUCT_CREATED_EVENT,
    PRODUCT_HIDDEN_EVENT,
    PRODUCT_UNHIDDEN_EVENT,
)
from app.infrastructure.clients.delivery.client import DeliveryClient
from app.infrastructure.clients.search.client import SearchIndex
from app.infrastructure.kafka.handlers.order_delivered import (
    create_handler as create_order_delivered_handler,
)
from app.infrastructure.kafka.handlers.order_payment_succeeded import (
    create_handler as create_order_payment_succeeded_handler,
)
from app.infrastructure.kafka.handlers.product_created import (
    create_handler as create_product_created_handler,
)
from app.infrastructure.kafka.handlers.product_hidden import (
    create_handler as create_product_hidden_handler,
)
from app.infrastructure.kafka.handlers.product_unhidden import (
    create_handler as create_product_unhidden_handler,
)
from app.infrastructure.kafka.schemas.events import EventEnvelope

EventHandler = Callable[[EventEnvelope], Awaitable[None]]

HANDLERS: dict[str, EventHandler] = {}


def register_handler(event_type: str, handler: EventHandler) -> None:
    HANDLERS[event_type] = handler


async def route_event(event: EventEnvelope) -> None:
    handler = HANDLERS.get(event.event_type)
    if handler is None:
        return
    await handler(event)


def register_commerce_handlers(
    session_factory: async_sessionmaker[AsyncSession],
    delivery_client: DeliveryClient,
    search_index: SearchIndex,
) -> None:
    register_handler(
        ORDER_PAYMENT_SUCCEEDED_EVENT,
        create_order_payment_succeeded_handler(session_factory, delivery_client),
    )
    register_handler(
        ORDER_DELIVERED_EVENT,
        create_order_delivered_handler(session_factory),
    )
    register_handler(
        PRODUCT_CREATED_EVENT,
        create_product_created_handler(session_factory, search_index),
    )
    register_handler(
        PRODUCT_HIDDEN_EVENT,
        create_product_hidden_handler(session_factory, search_index),
    )
    register_handler(
        PRODUCT_UNHIDDEN_EVENT,
        create_product_unhidden_handler(session_factory, search_index),
    )
