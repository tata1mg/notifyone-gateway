from commonutils.utils import CustomEnum


class ErrorMessages(CustomEnum):
    MISSING_REQUIRED_PARAMS = "missing required parameter - {}"
    INVALID_EMAIL_FORMAT = "invalid email format"
    INVALID_MOBILE_FORMAT = "invalid mobile format"
    EMAIL_MANDATORY_FOR_EVENT = 'email is mandatory to send notificatios for this event'
    MOBILE_MANDATORY_FOR_EVENT = 'mobile is mandatory to send notificatios for this event'
    INVALID_EVENT_PRIORITY = 'invalid event priority'
    EVENT_NOT_CONFIGURED = "Event not configured, configure it first. If you configured a new event recently, wait for few minnutes before you start sending notifications for that event"
    NO_CHANNEL_ACTIVE = "No notification channels are active for this event. Please enable at least one channel to send notifications"
    ONLY_ONE_TO_EMAIL_SUPPORTED = "Currently, only one email address is supported in 'to' address"
    ONLY_ONE_TO_MOBILE_SUPPORTED = "Currently, only one mobile number is supported in 'to' address"
    ONLY_ONE_TO_DEVICE_SUPPORTED = "Currently, only one device is supported in 'to' address for this push request"
    INVALID_ATTACHMENT_DATA = "Invalid attachment data - attachments must be a list of objects with each object containing exactly two properties - 'url' and 'filename'"
