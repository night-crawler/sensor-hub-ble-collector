import struct
from dataclasses import dataclass

from loguru import logger

from conv import deserialize_temperature, deserialize_pressure, deserialize_humidity
from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.abstract_service import AbstractService
from service.state import ServiceState


@dataclass
class Bme280State(ServiceState):
    temperature: NotifiableCharacteristic
    pressure: NotifiableCharacteristic
    humidity: NotifiableCharacteristic
    timeout: NotifiableCharacteristic


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
            timeout=self.gauge(
                uuid='a0e4a2ba-0000-8000-0000-00805f9b34fb', deserialize_fn=deserialize_humidity,
                metric_name='timeout', documentation='BME280 Timeout', unit='ms',
            ),
        )

    async def set_timeout_ms(self, timeout: int):
        ch = self.service.get_characteristic(self.state.timeout.uuid)
        data = timeout.to_bytes(4, 'little', signed=False)
        await self.client.write_gatt_char(ch, data, response=True)

    async def set_calibration(self, humidity: float = 0.0, temperature: float = 0.0, pressure: float = 0.0):
        humidity_ch = self.service.get_characteristic('a0e4a2ba-1234-4321-0001-00805f9b34fb')
        temperature_ch = self.service.get_characteristic('a0e4a2ba-1234-4321-0002-00805f9b34fb')
        pressure_ch = self.service.get_characteristic('a0e4a2ba-1234-4321-0003-00805f9b34fb')

        # pack little endian f32 value

        h = struct.pack('<f', humidity)
        t = struct.pack('<f', temperature)
        p = struct.pack('<f', pressure)

        assert len(h) == 4

        await self.client.write_gatt_char(humidity_ch, h, response=True)
        await self.client.write_gatt_char(temperature_ch, t, response=True)
        await self.client.write_gatt_char(pressure_ch, p, response=True)

        logger.info('Set calibration to humidity={}, temperature={}, pressure={}', humidity, temperature, pressure)
