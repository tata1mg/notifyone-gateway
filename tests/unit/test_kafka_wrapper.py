"""
Unit tests for gateway KafkaWrapper.
Stubs out commonutils/torpedo/sanic so this runs without the full pipenv install.
"""
import asyncio
import dataclasses
import enum
import importlib.util
import os
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Bootstrap stubs BEFORE importing anything from app.*
# ---------------------------------------------------------------------------

def _ensure_stub(name, **attrs):
    """Create a stub module if it isn't already present."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
    return sys.modules[name]


_ensure_stub("commonutils", BaseSQSWrapper=object)
_ensure_stub("commonutils.utils", CustomEnum=str)


class _FakeCONFIG:
    config = {
        "TRIGGER_NOTIFICATIONS": {
            "QUEUE_BACKEND": "sqs",
            "SQS": {},
            "KAFKA": {"BOOTSTRAP_SERVERS": "localhost:9092", "MAX_RETRY_ATTEMPTS": 3},
            "CRITICAL_PRIORITY": {"HOST": "http://localhost:9402"},
            "HIGH_PRIORITY": {"QUEUE_NAME": "stag-ns_high"},
            "MEDIUM_PRIORITY": {"QUEUE_NAME": "stag-ns_medium"},
            "LOW_PRIORITY": {"QUEUE_NAME": "stag-ns_low"},
        }
    }


class _BadRequest(Exception):
    pass


_ensure_stub("torpedo", CONFIG=_FakeCONFIG())
_ensure_stub("torpedo.exceptions", BadRequestException=_BadRequest)


class _NotificationRequestLogStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class _ProcessingType(str, enum.Enum):
    SYNC = "SYNC"
    ASYNC = "ASYNC"
    UNKNOWN = "UNKNOWN"


_ensure_stub(
    "app.constants",
    NotificationRequestLogStatus=_NotificationRequestLogStatus,
    ProcessingType=_ProcessingType,
)


@dataclasses.dataclass
class _PublishResult:
    is_success: bool
    status: object
    processing_type: object
    message: object = None
    extras: object = None

    def __post_init__(self):
        if self.extras is None:
            self.extras = {}


class _Publisher:
    PROCESSING_TYPE = None

    async def publish(self, data):
        raise NotImplementedError


_ensure_stub("app.services")
_ensure_stub("app.services.publisher", PublishResult=_PublishResult, Publisher=_Publisher)
_ensure_stub("app.utilities")
_ensure_stub("app.utilities.utils", json_dumps=json.dumps)
_ensure_stub("app.utilities.pubsub")

# Load the kafka_wrapper module directly from its file path
_GATEWAY_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _GATEWAY_ROOT not in sys.path:
    sys.path.insert(0, _GATEWAY_ROOT)

_spec = importlib.util.spec_from_file_location(
    "gateway_kafka_wrapper",
    f"{_GATEWAY_ROOT}/app/utilities/pubsub/kafka/kafka_wrapper.py",
)
_kafka_wrapper_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_kafka_wrapper_mod)

KafkaWrapper = _kafka_wrapper_mod.KafkaWrapper


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def kafka_config():
    return {
        "QUEUE_BACKEND": "kafka",
        "KAFKA": {
            "BOOTSTRAP_SERVERS": "localhost:9092",
            "MAX_RETRY_ATTEMPTS": 3,
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_success(kafka_config):
    """publish() returns PublishResult(is_success=True) on producer.send_and_wait success."""
    with patch.object(_kafka_wrapper_mod, "AIOKafkaProducer") as MockProducer:
        mock_producer = AsyncMock()
        MockProducer.return_value = mock_producer
        mock_producer.send_and_wait = AsyncMock(return_value=None)

        wrapper = KafkaWrapper(topic_name="test-topic", config=kafka_config)
        result = await wrapper.publish({"key": "value"})

    assert result.is_success is True
    assert result.message == "Message successfully published to Kafka"
    mock_producer.send_and_wait.assert_called_once()


@pytest.mark.asyncio
async def test_publish_failure(kafka_config):
    """publish() returns is_success=False on producer exception."""
    with patch.object(_kafka_wrapper_mod, "AIOKafkaProducer") as MockProducer:
        mock_producer = AsyncMock()
        MockProducer.return_value = mock_producer
        mock_producer.send_and_wait = AsyncMock(side_effect=Exception("broker unavailable"))

        wrapper = KafkaWrapper(topic_name="test-topic", config=kafka_config)
        result = await wrapper.publish({"key": "value"})

    assert result.is_success is False
    assert "broker unavailable" in result.message


@pytest.mark.asyncio
async def test_large_payload_triggers_compression(kafka_config):
    """A payload larger than 250KB triggers compression and adds compressedMessage header."""
    with patch.object(_kafka_wrapper_mod, "AIOKafkaProducer") as MockProducer:
        mock_producer = AsyncMock()
        MockProducer.return_value = mock_producer
        mock_producer.send_and_wait = AsyncMock(return_value=None)

        wrapper = KafkaWrapper(topic_name="test-topic", config=kafka_config)
        large_payload = {"data": "x" * (251 * 1000)}
        result = await wrapper.publish(large_payload)

    assert result.is_success is True
    call_args = mock_producer.send_and_wait.call_args
    headers = call_args.kwargs.get("headers")
    if headers is None:
        headers = call_args[1].get("headers", [])
    header_dict = dict(headers)
    assert header_dict.get("compressedMessage") == b"yes"


@pytest.mark.asyncio
async def test_init_is_idempotent(kafka_config):
    """init() is idempotent: producer.start() called only once on repeated init() calls."""
    with patch.object(_kafka_wrapper_mod, "AIOKafkaProducer") as MockProducer:
        mock_producer = AsyncMock()
        MockProducer.return_value = mock_producer

        wrapper = KafkaWrapper(topic_name="test-topic", config=kafka_config)
        await wrapper.init()
        await wrapper.init()
        await wrapper.init()

    mock_producer.start.assert_called_once()
    assert MockProducer.call_count == 1
