import asyncio
import json
import logging
import sys
import zlib
import base64

from aiokafka import AIOKafkaProducer

from app.constants import NotificationRequestLogStatus, ProcessingType
from app.services.publisher import Publisher, PublishResult

logger = logging.getLogger(__name__)


class KafkaWrapper(Publisher):

    PROCESSING_TYPE = ProcessingType.ASYNC

    def __init__(
            self,
            topic_name: str,
            config: dict = {},
            is_compression_enabled: bool = False,
    ):
        config = config or {}
        self.topic_name = topic_name
        self._kafka_config = config.get("KAFKA") or {}
        self.bootstrap_servers = self._kafka_config.get("BOOTSTRAP_SERVERS", "localhost:9092")
        self.max_retry_attempts = self._kafka_config.get("MAX_RETRY_ATTEMPTS", 3)
        self.is_compression_enabled = is_compression_enabled
        self._producer = None
        self._init_lock = asyncio.Lock()
        self._is_client_created = False

    async def init(self) -> None:
        if not self._is_client_created:
            async with self._init_lock:
                if not self._is_client_created:
                    self._producer = AIOKafkaProducer(
                        bootstrap_servers=self.bootstrap_servers
                    )
                    await self._producer.start()
                    self._is_client_created = True

    async def close_client(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            self._is_client_created = False

    async def publish(self, payload: dict, attributes: dict = None, **kwargs) -> PublishResult:
        await self.init()
        payload_json = json.dumps(payload)
        headers = []
        if self.is_compression_enabled or self._check_if_compression_needed(payload_json):
            payload_json = self._compress_message(payload_json)
            headers.append(("compressedMessage", b"yes"))
        try:
            await self._producer.send_and_wait(
                self.topic_name,
                value=payload_json.encode("utf-8"),
                headers=headers,
            )
            return PublishResult(
                is_success=True,
                processing_type=self.PROCESSING_TYPE,
                status=NotificationRequestLogStatus.SUCCESS,
                message="Message successfully published to Kafka",
            )
        except Exception as err:
            logger.error("Failed to publish to Kafka topic %s: %s", self.topic_name, str(err))
            return PublishResult(
                is_success=False,
                processing_type=self.PROCESSING_TYPE,
                status=NotificationRequestLogStatus.FAILED,
                message=str(err),
            )

    @staticmethod
    def _compress_message(message: str) -> str:
        compressed = zlib.compress(message.encode("utf-8"), 1)
        return base64.b64encode(compressed).decode("utf-8")

    @staticmethod
    def _check_if_compression_needed(payload_json: str) -> bool:
        if sys.getsizeof(payload_json) > 250 * 1000:
            return True
        return False
