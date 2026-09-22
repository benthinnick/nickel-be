import logging
from collections.abc import Sequence

from aiokafka import AIOKafkaConsumer
from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.kafka.handlers import route_event
from app.infrastructure.kafka.schemas.events import EventEnvelope
from app.infrastructure.serialization.json import loads
from app.observability import metrics
from app.observability.request_context import clear_kafka_context, set_kafka_context

logger = logging.getLogger(__name__)


class KafkaConsumer:
    def __init__(self, settings: Settings, topics: Sequence[str]) -> None:
        self._settings = settings
        self._topics = list(topics)
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        if not self._topics:
            logger.info("Kafka consumer not started: no topics configured")
            return
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._settings.kafka_brokers,
            client_id=self._settings.kafka_client_id,
            group_id=self._settings.kafka_group_id,
            enable_auto_commit=False,
        )
        await self._consumer.start()
        logger.info("Kafka consumer started", extra={"topics": self._topics})

    async def stop(self) -> None:
        if self._consumer is None:
            return
        await self._consumer.stop()
        self._consumer = None
        logger.info("Kafka consumer stopped")

    async def consume(self) -> None:
        if self._consumer is None:
            return
        async for message in self._consumer:
            metrics.increment("kafka_messages_consumed", topic=message.topic)
            set_kafka_context(
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )
            try:
                payload = loads(message.value)
                event = EventEnvelope.model_validate(payload)
                set_kafka_context(
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    event_id=str(event.event_id),
                )
                await route_event(event)
                await self._consumer.commit()
            except (ValidationError, ValueError, TypeError):
                metrics.increment("kafka_processing_failures", reason="malformed")
                logger.exception("Malformed Kafka event; skipping")
                await self._consumer.commit()
            except Exception:
                metrics.increment("kafka_processing_failures", reason="handler")
                logger.exception("Kafka handler failed")
                raise
            finally:
                clear_kafka_context()
