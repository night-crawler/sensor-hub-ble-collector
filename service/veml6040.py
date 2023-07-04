from dataclasses import dataclass

from conv import deserialize_int
from characteristic.notifiable_characteristic import NotifiableCharacteristic, DerivedMetric
from service.abstract_service import AbstractService
from service.state import ServiceState


@dataclass
class VEML6040State(ServiceState):
    red: NotifiableCharacteristic
    green: NotifiableCharacteristic
    blue: NotifiableCharacteristic
    white: NotifiableCharacteristic
    cct: NotifiableCharacteristic
    lux: NotifiableCharacteristic
    timeout: NotifiableCharacteristic

    def post_process(self, nch_name: str, notifiable_characteristic: NotifiableCharacteristic):
        if not self.lux.value or self.lux.value < 10:
            self.cct.reset()


class VEML6040Service(AbstractService):
    namespace = 'sensor_hub'
    subsystem = 'veml6040'
    state: VEML6040State

    def init_state(self):
        def post_process_cct(value):
            if not self.state.lux.value or self.state.lux.value < 10:
                return None
            return value

        self.state = VEML6040State(
            red=self.gauge(
                uuid='ebbbbaea-a000-0000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='red', documentation='red', unit='raw',
            ),
            green=self.gauge(
                uuid='eaeaeaea-b000-1000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='green', documentation='green', unit='raw',
            ),
            blue=self.gauge(
                uuid='eaeaeaea-c000-2000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='blue', documentation='blue', unit='raw',
            ),
            white=self.gauge(
                uuid='eaeaeaea-d000-3000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='white', documentation='white', unit='raw',
            ),
            cct=self.gauge(
                uuid='2AE9', deserialize_fn=deserialize_int,
                metric_name='cct', documentation='Correlated Color Temperature', unit='kelvin',
                post_process_fn=post_process_cct
            ),
            lux=self.gauge(
                uuid='2AFF', deserialize_fn=deserialize_int,
                metric_name='lux', documentation='Luminous Flux', unit='lumen',
            ),
            timeout=self.gauge(
                uuid='a0e4a2ba-0000-8000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='timeout', documentation='Timeout', unit='count',
            ),
        )

