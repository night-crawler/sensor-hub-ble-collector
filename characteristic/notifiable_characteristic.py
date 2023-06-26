from dataclasses import dataclass
from typing import Optional, Any

from loguru import logger
from prometheus_client.registry import Collector


@dataclass
class NotifiableCharacteristic:
    uuid: str
    deserialize_fn: callable
    metric: Collector
    label_dict: dict
    value: Optional[Any] = None

    @logger.catch
    def update_value(self, value: bytearray):
        self.value = self.deserialize_fn(value)
        self.metric.labels(**self.label_dict).set(self.value)

    @property
    def display_name(self):
        return f'{self.metric._name}={self.value}'
