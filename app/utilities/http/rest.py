from typing import Any, Dict

from urllib import parse as urlparse

from torpedo.base_http_request import BaseHttpRequest

from app.constants import NotificationRequestLogStatus, ProcessingType
from app.services.publisher import Publisher, PublishResult


class RestApiClientWrapper(Publisher):
    PROCESSING_TYPE = ProcessingType.SYNC

    def __init__(self, host: str, endpoint: str, method: str):
        self._host = host
        self._endpoint = endpoint
        self._method = method

    async def publish(self, payload: Dict[str, Any]) -> PublishResult:
        url = urlparse.urljoin(self._host, self._endpoint)
        response = await BaseHttpRequest.request(
            self._method,
            url,
            data=payload,
            headers={"content-type": "application/json"},
        )
        if response.status == 200:
            publish_result = PublishResult(
                is_success=True,
                processing_type=self.PROCESSING_TYPE,
                status=NotificationRequestLogStatus.SUCCESS,
                message="Message processed via RestClient",
                extras=response.data.get("data"),
            )
        else:
            publish_result = PublishResult(
                is_success=False,
                processing_type=self.PROCESSING_TYPE,
                status=NotificationRequestLogStatus.FAILED,
                message="Something went wrong",
                extras=response.data.get("error", {}).get("message", {}),
            )
        return publish_result
