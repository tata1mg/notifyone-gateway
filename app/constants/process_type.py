from commonutils.utils import CustomEnum


class ProcessingType(str, CustomEnum):
    SYNC = "SYNC"
    ASYNC = "ASYNC"
    UNKNOWN = "UNKNOWN"

    def __str__(self):
        return self.value
