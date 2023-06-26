from dataclasses import dataclass

from bleak import BleakGATTCharacteristic
from loguru import logger

from characteristic.notifiable_characteristic import NotifiableCharacteristic
from conv import deserialize_voltage, deserialize_temperature, deserialize_int
from service.abstract_service import AbstractService
from service.state import ServiceState


@dataclass
class DeviceInformationState(ServiceState):
    battery_voltage: NotifiableCharacteristic
    temperature: NotifiableCharacteristic
    timeout: NotifiableCharacteristic

    @logger.catch
    def update_characteristic(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        if characteristic.uuid.lower() == '00002bde-0000-1000-8000-00805f9b34fb'.lower():
            value = data.strip(b'\x00').decode('utf-8')
            logger.warning(value)
        else:
            super().update_characteristic(characteristic, data)


class DeviceInformationService(AbstractService):
    namespace: str = 'sensor_hub'
    subsystem: str = 'device_information'
    state: DeviceInformationState

    def init_state(self):
        self.state = DeviceInformationState(
            battery_voltage=self.gauge(
                uuid='00002b18-0000-1000-8999-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='battery_voltage', documentation='Battery voltage', unit='volts',
            ),
            temperature=self.gauge(
                uuid='00002a6e-0000-1000-8000-00805f9b34fb', deserialize_fn=deserialize_temperature,
                metric_name='temperature', documentation='Temperature', unit='degrees_celsius',
            ),
            timeout=self.gauge(
                uuid='00002b18-0002-1000-8000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='timeout', documentation='Timeout', unit='seconds',
            ),
        )
