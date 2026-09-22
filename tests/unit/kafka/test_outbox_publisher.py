from uuid import uuid4

from app.core.constants import ORDERS_TOPIC
from app.infrastructure.kafka.outbox_publisher import OutboxPublisher
from app.repositories.outbox_repository import SqlOutboxRepository


class RecordingProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict, str | None]] = []

    async def publish(self, topic: str, value: dict, *, key: str | None = None) -> None:
        self.messages.append((topic, value, key))


async def test_outbox_publisher_publishes_and_marks_published(session_factory, db_session) -> None:
    repository = SqlOutboxRepository(db_session)
    order_id = uuid4()
    event_id = await repository.enqueue(
        event_type="order_created",
        aggregate_id=order_id,
        payload={"order_id": str(order_id)},
    )
    await db_session.commit()

    producer = RecordingProducer()
    publisher = OutboxPublisher(session_factory, producer)
    published = await publisher.publish_pending()

    assert published == 1
    assert len(producer.messages) == 1
    topic, value, key = producer.messages[0]
    assert topic == ORDERS_TOPIC
    assert key == str(order_id)
    assert value["event_id"] == str(event_id)
    assert value["event_type"] == "order_created"

    async with session_factory() as session:
        remaining = await SqlOutboxRepository(session).list_unpublished(limit=10)
        assert remaining == []
