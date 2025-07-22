import logging
from typing import Dict

from torpedo import CONFIG
from torpedo.exceptions import BadRequestException

from .notifications import Notifications
from .publisher import Publisher

from app.constants import ErrorMessages, EventPriority, PrepareNotification
from app.models import Event
from app.utilities import generate_uuid
from app.utilities.pubsub import SQSWrapper
from app.utilities.http import RestApiClientWrapper
from app.utilities.validators import validate_email, validate_mobile
from app.utilities.parser import V2PayloadParser

logger = logging.getLogger()

notification_config = CONFIG.config["TRIGGER_NOTIFICATIONS"]


class EventNotification:

    HANDLERS: Dict[EventPriority, Publisher]

    @classmethod
    def setup(cls):
        critical_p_config = notification_config["CRITICAL_PRIORITY"]
        critical_priority_handler = RestApiClientWrapper(
            host=critical_p_config.get("HOST"),
            endpoint=PrepareNotification.ENDPOINT,
            method=PrepareNotification.METHOD,
        )
        high_priority_handler = SQSWrapper(
            notification_config["HIGH_PRIORITY"]["QUEUE_NAME"],
            config=notification_config,
        )
        medium_priority_handler = SQSWrapper(
            notification_config["MEDIUM_PRIORITY"]["QUEUE_NAME"],
            config=notification_config,
        )
        low_priority_handler = SQSWrapper(
            notification_config["LOW_PRIORITY"]["QUEUE_NAME"],
            config=notification_config,
        )

        cls.HANDLERS = {
            EventPriority.CRITICAL: critical_priority_handler,
            EventPriority.HIGH: high_priority_handler,
            EventPriority.MEDIUM: medium_priority_handler,
            EventPriority.LOW: low_priority_handler,
        }

    @staticmethod
    def _validate_notification_request(event: Event, payload: dict):
        to_addresses = payload.get('to') or dict()
        email_addresses = to_addresses.get('email') or list()
        mobile_numbers = to_addresses.get('mobile') or list()

        for email in email_addresses:
            if not validate_email(email):
                raise BadRequestException(ErrorMessages.INVALID_EMAIL_FORMAT.value)

        for mobile in mobile_numbers:
            if not validate_mobile(mobile):
                raise BadRequestException(ErrorMessages.INVALID_MOBILE_FORMAT.value)

        if not event.any_channel_active():
            raise BadRequestException(ErrorMessages.NO_CHANNEL_ACTIVE.value)
        # Validate attachments - it must be a list of dicts
        if payload.get("attachments"):
            attachments = payload["attachments"]
            if not isinstance(attachments, list):
                raise BadRequestException(ErrorMessages.INVALID_ATTACHMENT_DATA.value)
            for attachment in attachments:
                if not isinstance(attachment, dict) or 'url' not in attachment or 'filename' not in attachment:
                    raise BadRequestException(ErrorMessages.INVALID_ATTACHMENT_DATA.value)

        if event.dynamic_channel_allowed:
            allowed_channels = payload.get("channels")
            # if no channels are provided, at least one channel should be active
            if allowed_channels == []:
                raise BadRequestException(ErrorMessages.NO_CHANNEL_ACTIVE.value)
            # if channels are provided, they should be subset of allowed channels
            if allowed_channels:
                if not set(allowed_channels).issubset(event.get_active_channels()):
                    raise BadRequestException(ErrorMessages.INVALID_CHANNELS.value)
            
        # TODO - Need to put validation around verifying the input devices

    @classmethod
    async def trigger_event_notification(cls, payload: dict):
        event_id = str(payload.get("event_id", ""))
        app_name = payload.get("app_name", "")
        event_name = payload.get("event_name", "")
        
        if not event_id:
            event = await Notifications.get_event(app_name, event_name)
        else:
            event = await Notifications.get_event_by_id(event_id)
        if not event:
            raise BadRequestException(ErrorMessages.EVENT_NOT_CONFIGURED.value)
        
        payload = V2PayloadParser.parse(payload)
        cls._validate_notification_request(event, payload)

        to_addresses = payload.get('to') or dict()
        email_addresses = to_addresses.get('email') or list()
        mobile_numbers = to_addresses.get('mobile') or dict()
        devices = to_addresses.get('device') or list()

        request_id = generate_uuid()

        final_payload = {
            "request_id": request_id,
            "app_name": event.app_name,
            "event_name": event.event_name,
            "event_id": payload["event_id"],
            "source_identifier": payload["source_identifier"],
            "to": {
                "email": email_addresses,
                "mobile": mobile_numbers,
                "device": devices
            },
            "channels": {
                "email": payload.get("channels", dict()).get("email") or dict(),
                "whatsapp": payload.get("channels", dict()).get("whatsapp") or dict()
            },
            "attachments": payload.get("attachments") or list(),
            "body": payload.get("body") or dict()
        }
        result = await cls.accept_notification_request(event, final_payload)        
        return {
            "request_id": request_id, 
            "processing_type": result.processing_type, 
            "message": result.message, 
            **result.extras,
        }

    @classmethod
    async def accept_notification_request(cls, event: Event, data):
        handler = cls.HANDLERS.get(event.priority)
        if not handler:
            raise BadRequestException(ErrorMessages.INVALID_EVENT_PRIORITY.value)

        published = await handler.publish(data)
        if not published.is_success:
            logger.error(
                "Could not publish notification request through handler - %s",
                handler,
            )
            raise BadRequestException(
                "Could not accept this request, please try again after some time"
            )
        return published
