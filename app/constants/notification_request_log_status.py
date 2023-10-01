from commonutils.utils import CustomEnum


class NotificationRequestLogStatus(str, CustomEnum):
    NEW = "NEW"
    INITIATED = "INITIATED"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
    USER_OPT_OUT = "USER_OPT_OUT"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"

    def __str__(self):
        return self.value
