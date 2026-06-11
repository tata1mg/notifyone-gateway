__all__ = ["SQSWrapper", "KafkaWrapper", "get_publisher"]

from .sqs import SQSWrapper
from .kafka import KafkaWrapper


def get_publisher(queue_name: str, config: dict = {}, **kwargs):
    config = config or {}
    backend = config.get("QUEUE_BACKEND", "sqs").lower()
    if backend == "kafka":
        return KafkaWrapper(topic_name=queue_name, config=config, **kwargs)
    return SQSWrapper(queue_name, config=config, **kwargs)
