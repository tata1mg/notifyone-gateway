import aiotask_context as context
from torpedo import BaseApiRequest
from torpedo.constants import X_SHARED_CONTEXT


class APIClient(BaseApiRequest):
    """
    Base class for all inter service requests. Each method will return

    AsyncTaskResponse(self._data['data'],
                      meta=self._data.get('meta', None),
                      status_code=self._data['status_code'],
                      headers=headers)
    """

    _timeout = None

    @classmethod
    def get_inter_service_headers(
        cls, headers_keys: list = None, get_shared_context=False
    ):
        headers_keys = headers_keys or list()
        _headers = {}
        headers = {}
        if headers:
            if headers_keys:
                for _key in headers_keys:
                    _headers[_key] = headers.get(_key)
            else:
                _headers = headers
            if get_shared_context:
                if context.get(X_SHARED_CONTEXT):
                    _headers[X_SHARED_CONTEXT] = context.get(X_SHARED_CONTEXT)
        return _headers
