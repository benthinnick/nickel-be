import logging

from aiokafka import AIOKafkaProducer

from app.core.config import Settings
from app.infrastructure.serialization.json import dumps
from app.observability import metrics

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka_brokers,
            client_id=self._settings.kafka_client_id,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None
        logger.info("Kafka producer stopped")

    async def publish(self, topic: str, value: dict, *, key: str | None = None) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")
        encoded_key = key.encode("utf-8") if key else None
        await self._producer.send_and_wait(topic, dumps(value).encode("utf-8"), key=encoded_key)
        metrics.increment("kafka_messages_produced", topic=topic)
