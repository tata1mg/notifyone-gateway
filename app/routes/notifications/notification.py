import logging

from sanic import Blueprint
from sanic_openapi import openapi
from sanic_openapi.openapi3.definitions import Parameter
from torpedo import Request, send_response
from torpedo.exceptions import BadRequestException

from app.services import EventNotification, Notifications
from app.routes.notifications.api_model import GetNotificationApiModel, SendNotificationApiModel
from app.constants import ErrorMessages

event_notification_blueprint = Blueprint("event_notification")

logger = logging.getLogger()


@event_notification_blueprint.route(
    SendNotificationApiModel.uri(), methods=[SendNotificationApiModel.http_method()], name=SendNotificationApiModel.name()
)
@openapi.definition(
    summary=SendNotificationApiModel.summary(),
    description=SendNotificationApiModel.description(),
    body={
        SendNotificationApiModel.request_content_type(): SendNotificationApiModel.RequestBodyOpenApiModel
    },
    response={
        SendNotificationApiModel.response_content_type(): SendNotificationApiModel.ResponseBodyOpenApiModel
    },
)
async def send_event_notification(request: Request):
    """
    Endpoint to trigger event based notifications
    """
    request_payload = request.custom_json()
    event_id = request_payload.get('event_id')
    source_identifier = request_payload.get('source_identifier')
    to_addresses = request_payload.get('to') or dict()
    if not event_id:
        raise BadRequestException(ErrorMessages.MISSING_REQUIRED_PARAMS.value.format('event_id'))
    if not source_identifier:
        raise BadRequestException(ErrorMessages.MISSING_REQUIRED_PARAMS.value.format('source_identifier'))

    try:
        data = await EventNotification.trigger_event_notification(request_payload)
    except Exception as e:
        logger.error(
            "Request Failed - error type : {}, message : {}, params - {} {}".format(
                type(e), str(e), event_id, to_addresses
            )
        )
        raise e
    return send_response(data=data)


@event_notification_blueprint.route(
    GetNotificationApiModel.uri(), methods=[GetNotificationApiModel.http_method()], name=GetNotificationApiModel.name()
)
@openapi.definition(
    summary=GetNotificationApiModel.summary(),
    description=GetNotificationApiModel.description(),
    parameter=[Parameter('notification_request_id', openapi.String(), description="Unique ID generated by the Notification System", required=False), Parameter('source_identifier', openapi.String(), description="Source identifier sent with the request", required=False)],
    response={
        GetNotificationApiModel.response_content_type(): GetNotificationApiModel.ResponseBodyOpenApiModel
    },
)
async def get_event_notification(request: Request):
    """
    Endpoint to trigger event based notifications
    """
    request_payload = request.request_params()
    notification_request_id = request_payload.get('notification_request_id')
    source_identifier = request_payload.get('source_identifier')
    if not (notification_request_id or source_identifier):
        raise BadRequestException("Either notification_request_id OR source_identifier must be provided")

    try:
        data = await Notifications.get_event_notification(notification_request_id)
    except Exception as e:
        logger.error(
            "Request Failed - error type : {}, message : {}, params - {}".format(
                type(e), str(e), notification_request_id
            )
        )
        raise e
    return send_response(data=data)
