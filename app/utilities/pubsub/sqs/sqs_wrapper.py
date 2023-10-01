import asyncio
import sys
import zlib
import base64

from app.constants import NotificationRequestLogStatus, ProcessingType
from app.services.publisher import Publisher, PublishResult

from commonutils import BaseSQSWrapper

from app.utilities.utils import json_dumps, json_loads


class SQSWrapper(Publisher):
    PROCESSING_TYPE = ProcessingType.ASYNC

    def __init__(
            self,
            queue_name: str,
            config: dict = {},
            handler: object = None,
            is_compression_enabled: bool = False,
    ):
        config = config or {"SQS": {}}
        self.queue_name = queue_name
        self.sqs_manager = BaseSQSWrapper(config)
        self._create_client_lock = asyncio.Lock()
        self.handler = handler
        self.is_client_created = False
        self.is_compression_enabled = is_compression_enabled

    def __del__(self):
        asyncio.create_task(self.close_client())

    async def close_client(self):
        await self.sqs_manager.close()

    async def init(self):
        if not self.is_client_created:
            async with self._create_client_lock:
                if not self.is_client_created:
                    await self.sqs_manager.get_sqs_client(queue_name=self.queue_name)
            self.is_client_created = True

    async def publish(self, payload: dict, attributes=None, **kwargs) -> PublishResult:
        await self.init()
        attributes = attributes or dict()
        payload_json = json_dumps(payload)
        if self.is_compression_enabled:
            payload_json = self.compress_message(payload_json)
            attributes['compressedMessage'] = {
                "DataType": "String",
                "StringValue": "yes"
            }
        elif self.check_if_compression_needed(payload_json):
            payload_json = self.compress_message(payload_json)
            attributes['compressedMessage'] = {
                "DataType": "String",
                "StringValue": "yes"
            }
        try:
            response = await self.sqs_manager.publish_to_sqs(
                payload=payload_json, attributes=attributes, batch=False, **kwargs
            )
            return PublishResult(
                is_success=True,
                processing_type=self.PROCESSING_TYPE,
                status=NotificationRequestLogStatus.SUCCESS, 
                message="Message successfully published to SQS",
            )
        except Exception as err:
            return PublishResult(
                is_success=False,
                processing_type=self.PROCESSING_TYPE,
                status=NotificationRequestLogStatus.FAILED, 
                message=str(err),
            )

    def compress_payload(self, payload) -> str:
        payload_str = json_dumps(payload)
        return self.compress_message(payload_str)

    @staticmethod
    def compress_message(message: str):
        compressed_msg = zlib.compress(message.encode("utf-8"), 1)
        encoded_msg = base64.b64encode(compressed_msg).decode("utf-8")
        return encoded_msg

    def decompress_to_payload(self, compressed_msg) -> dict:
        decompressed_msg = self.decompress_message(compressed_msg)
        return json_loads(decompressed_msg)

    @staticmethod
    def decompress_message(compressed_msg: str):
        decoded_msg = base64.b64decode(compressed_msg.encode('utf-8'))
        decompressed_msg = zlib.decompress(decoded_msg).decode('utf-8')
        return decompressed_msg

    @staticmethod
    def check_if_compression_needed(payload_json: str) -> bool:
        """
        As AWS SQS supports messages up to 256KB only, compress if the payload size is > 250KB
        Keeping 6KB is for other details in message like messageAttributes etc.
        """
        if sys.getsizeof(payload_json) > 250*1000:
            return True
        return False
