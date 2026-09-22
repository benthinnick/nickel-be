import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.middleware.request_id import RequestIdMiddleware
from app.api.routes.auth import router as auth_router
from app.api.routes.carts import router as carts_router
from app.api.routes.health import router as health_router
from app.api.routes.orders import router as orders_router
from app.api.routes.products import router as products_router
from app.api.routes.sellers import router as sellers_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.infrastructure.clients.delivery.client import StubDeliveryClient
from app.infrastructure.database.session import (
    configure_database,
    create_tables,
    dispose_database,
    get_session_factory,
)
from app.infrastructure.http.client import create_http_client
from app.infrastructure.kafka.consumer import KafkaConsumer
from app.infrastructure.kafka.handlers import register_commerce_handlers
from app.infrastructure.kafka.outbox_publisher import OutboxPublisher
from app.infrastructure.kafka.producer import KafkaProducer
from app.infrastructure.kafka.topics import CONSUMER_TOPICS
from app.infrastructure.redis.client import create_redis_client
from app.observability.logging import configure_logging
from app.repositories.product_repository import seed_demo_catalog


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()

    configure_database(settings)
    await create_tables()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_demo_catalog(session)
        await session.commit()

    http_client = create_http_client(settings)
    app.state.http_client = http_client

    redis = create_redis_client(settings)
    app.state.redis = redis

    delivery_client = StubDeliveryClient()
    app.state.delivery_client = delivery_client
    register_commerce_handlers(get_session_factory(), delivery_client)

    producer: KafkaProducer | None = None
    consumer: KafkaConsumer | None = None
    consumer_task: asyncio.Task[None] | None = None
    publisher: OutboxPublisher | None = None
    publisher_task: asyncio.Task[None] | None = None

    if settings.kafka_enabled:
        producer = KafkaProducer(settings)
        await producer.start()
        publisher = OutboxPublisher(
            get_session_factory(),
            producer,
            poll_interval_seconds=settings.outbox_poll_interval_seconds,
        )
        publisher_task = asyncio.create_task(publisher.run())
        consumer = KafkaConsumer(settings, topics=CONSUMER_TOPICS)
        await consumer.start()
        consumer_task = asyncio.create_task(consumer.consume())

    app.state.kafka_producer = producer

    try:
        yield
    finally:
        if publisher_task is not None:
            publisher_task.cancel()
            try:
                await publisher_task
            except asyncio.CancelledError:
                pass
        if consumer_task is not None:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        if consumer is not None:
            await consumer.stop()
        if producer is not None:
            await producer.stop()
        await http_client.aclose()
        await redis.aclose()
        await dispose_database()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Shekel API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = settings
    register_exception_handlers(application)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(health_router)
    application.include_router(products_router, prefix="/api/v1")
    application.include_router(users_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(sellers_router, prefix="/api/v1")
    application.include_router(carts_router, prefix="/api/v1")
    application.include_router(orders_router, prefix="/api/v1")
    return application


app = create_app()
