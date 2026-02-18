from torpedo import CONFIG

from app.service_clients.base_api_client import APIClient


class NotifyOneCoreClient(APIClient):
    """
    auth service client
    """
    ns_config = CONFIG.config['NOTIFICATION_SERVICE']
    _host = ns_config['HOST']
    _timeout = ns_config['TIMEOUT']

    @classmethod
    async def get_events_custom(cls, attributes: list=None):
        """
        By default, this routine returns just the id, event_name and app_name details. Add extra attributes needed
        in the event_other_details param
        :param attributes: list of event attributes needed in the response
        :return:
        """
        # TODO remove this mocking after dev test
        path = '/events/custom'
        attributes = attributes or list()
        attributes_str = ','.join(attributes)
        params = {
            'attributes': attributes_str
        }
        result = await cls.get(path, query_params=params)
        return result.data

    @classmethod
    async def get_sent_notifications_by_notification_request_id(cls, notification_request_id):
        path = '/notifications/{notification_request_id}'.format(notification_request_id=notification_request_id)
        result = await cls.get(path)
        return result.data
    
    @classmethod
    async def handle_email_template_update(cls, data):
        path = '/events/handle-email-template-update'
        result = await cls.post(path, data=data)
        return result.data
