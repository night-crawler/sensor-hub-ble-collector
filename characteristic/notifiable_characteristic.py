from dataclasses import dataclass
from typing import Optional, Any

from loguru import logger
from prometheus_client.metrics import MetricWrapperBase

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.state import ServiceState


class MetricResetMixin:
    label_dict: dict
    metric: MetricWrapperBase

    def reset(self):
        label_values = frozenset(self.label_dict.values())
        with self.metric._lock:
            self.metric._metrics = {
                k: v for k, v in self.metric._metrics.items()
                if frozenset(k) != label_values
            }


class DisplayMixin:
    @property
    def display_name(self):
        return f'{self.metric._name}={self.value}'


@dataclass
class NotifiableCharacteristic(MetricResetMixin, DisplayMixin):
    uuid: str
    deserialize_fn: callable
    metric: MetricWrapperBase
    label_dict: dict
    value: Optional[Any] = None
    post_process_fn: callable = lambda x: x

    @logger.catch
    def update_value(self, value: bytearray):
        self.value = self.deserialize_fn(value)
        self.value = self.post_process_fn(self.value)

        if self.value is not None:
            self.metric.labels(**self.label_dict).set(self.value)
        else:
            self.reset()


@dataclass
class DerivedMetric(MetricResetMixin, DisplayMixin):
    triggered_by: set[str]
    metric: MetricWrapperBase
    label_dict: dict
    value_fn: callable
    value: Optional[Any] = None
    post_process_fn: callable = lambda x: x

    @logger.catch
    def update_value(self, state: 'ServiceState', notifiable_characteristic: NotifiableCharacteristic):
        self.value = self.value_fn(state, notifiable_characteristic)
        self.value = self.post_process_fn(self.value)

        if self.value is not None:
            self.metric.labels(**self.label_dict).set(self.value)
        else:
            self.reset()
