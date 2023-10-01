from typing import Any, Dict, Optional

import abc
from dataclasses import dataclass

from app.constants import NotificationRequestLogStatus, ProcessingType
from app.utilities.dataclass import JSONSerializableDataClass


@dataclass
class OperatorDetails(JSONSerializableDataClass):
    name: str
    event_id: Optional[str] = None


@dataclass
class PublishResult(JSONSerializableDataClass):
    is_success: bool
    status: NotificationRequestLogStatus
    processing_type: ProcessingType
    message: Any = None
    extras: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.extras is None:
            self.extras = {}


class Publisher(abc.ABC):
    PROCESSING_TYPE = ProcessingType.UNKNOWN

    @abc.abstractmethod
    async def publish(self, data: Dict) -> PublishResult:
        raise NotImplementedError
