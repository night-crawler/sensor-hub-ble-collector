from dataclasses import dataclass

from conv import deserialize_temperature, deserialize_pressure, deserialize_humidity
from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.abstract_service import AbstractService
from service.state import ServiceState


@dataclass
class Bme280State(ServiceState):
    temperature: NotifiableCharacteristic
    pressure: NotifiableCharacteristic
    humidity: NotifiableCharacteristic


class Bme280Service(AbstractService):
    namespace = 'sensor_hub'
    subsystem = 'bme280'
    state: Bme280State

    def init_state(self):
        self.state = Bme280State(
            temperature=self.gauge(
                uuid='00002a6e-0000-1000-8000-00805f9b34fb', deserialize_fn=deserialize_temperature,
                metric_name='temperature', documentation='BME280 Temperature', unit='degrees_celsius',
            ),
            pressure=self.gauge(
                uuid='00002a6d-0000-1000-8000-00805f9b34fb', deserialize_fn=deserialize_pressure,
                metric_name='pressure', documentation='BME280 Pressure', unit='pa',
            ),
            humidity=self.gauge(
                uuid='00002a6f-0000-1000-8000-00805f9b34fb', deserialize_fn=deserialize_humidity,
                metric_name='humidity', documentation='BME280 Humidity', unit='percent',
            ),
        )
