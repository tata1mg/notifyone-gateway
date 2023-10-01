from commonutils.utils import CustomEnum


class NotificationChannels(CustomEnum):
    EMAIL = 'email'
    SMS = 'sms'
    WHATSAPP = 'whatsapp'
    PUSH = 'push'
    CALL = 'call'

    @classmethod
    def email_mandatory_channels(cls):
        return [cls.EMAIL.value]

    @classmethod
    def mobile_mandatory_channels(cls):
        return [cls.SMS.value, cls.WHATSAPP.value, cls.CALL.value]
