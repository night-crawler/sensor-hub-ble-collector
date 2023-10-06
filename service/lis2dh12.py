from dataclasses import dataclass

from conv import deserialize_int, deserialize_float
from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.abstract_service import AbstractService
from service.state import ServiceState


@dataclass
class LIS2DH12State(ServiceState):
    x: NotifiableCharacteristic
    y: NotifiableCharacteristic
    z: NotifiableCharacteristic
    timeout: NotifiableCharacteristic


class LIS2DH12Service(AbstractService):
    namespace = 'sensor_hub'
    subsystem = 'lis2dh12'
    state: LIS2DH12State

    def init_state(self):
        self.state = LIS2DH12State(
            x=self.gauge(
                uuid='eaeaeaea-0000-0000-0000-00805f9b34fb', deserialize_fn=deserialize_float,
                metric_name='x', documentation='X acceleration', unit='ms2',
            ),
            y=self.gauge(
                uuid='eaeaeaea-0000-1000-0000-00805f9b34fb', deserialize_fn=deserialize_float,
                metric_name='y', documentation='Y acceleration', unit='ms2',
            ),
            z=self.gauge(
                uuid='eaeaeaea-0000-2000-0000-00805f9b34fb', deserialize_fn=deserialize_float,
                metric_name='z', documentation='Z acceleration', unit='ms2',
            ),
            timeout=self.gauge(
                uuid='a0e4a2ba-0000-8000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='timeout', documentation='Timeout', unit='count',
            ),
        )

    async def set_timeout_ms(self, timeout: int):
        ch = self.service.get_characteristic(self.state.timeout.uuid)
        data = timeout.to_bytes(4, 'little', signed=False)
        await self.client.write_gatt_char(ch, data, response=True)
