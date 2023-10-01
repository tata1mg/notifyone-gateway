from typing import ClassVar, List, Optional

from app.utilities.utils import json_dumps
from dataclasses import dataclass, asdict, field


@dataclass
class JSONSerializableDataClass:
    __SERIALIZABLE_KEYS__: ClassVar[Optional[List[str]]] = field(init=False)

    def __post_init__(self):
        ser_keys = getattr(self, "__SERIALIZABLE_KEYS__", None)
        if ser_keys is not None and not isinstance(ser_keys, list):
            raise ValueError("SERIALIZABLE_KEYS must be a list of strings or None")

    @property
    def __dict__(self):
        ser_keys = getattr(self, "__SERIALIZABLE_KEYS__", None)
        data_dict = asdict(self)
        if ser_keys is not None:
            return {key: data_dict[key] for key in self.__SERIALIZABLE_KEYS__}
        return data_dict

    @property
    def json(self):
        return json_dumps(self.__dict__)
