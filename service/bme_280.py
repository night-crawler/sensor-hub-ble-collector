import struct
from dataclasses import dataclass

from loguru import logger

from conv import deserialize_temperature, deserialize_pressure, deserialize_humidity
from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.abstract_service import AbstractService
from service.state import ServiceState
from pythermalcomfort.psychrometrics import psy_ta_rh


@dataclass
class Bme280State(ServiceState):
    temperature: NotifiableCharacteristic
    pressure: NotifiableCharacteristic
    humidity: NotifiableCharacteristic
    timeout: NotifiableCharacteristic

    p_sat: NotifiableCharacteristic
    p_vap: NotifiableCharacteristic
    hr: NotifiableCharacteristic
    t_wb: NotifiableCharacteristic
    t_dp: NotifiableCharacteristic
    enthalpy: NotifiableCharacteristic


def calculate_psychrometric_values(state: Bme280State):
    if None in (state.temperature.value, state.humidity.value, state.pressure.value):
        return {}
    return psy_ta_rh(tdb=state.temperature.value, rh=state.humidity.value, p_atm=state.pressure.value)


def enthalpy_value_fn(state, _ch: NotifiableCharacteristic):
    return calculate_psychrometric_values(state).get('h')


def t_wb_value_fn(state, _ch: NotifiableCharacteristic):
    return calculate_psychrometric_values(state).get('t_wb')


def t_dp_value_fn(state, _ch: NotifiableCharacteristic):
    return calculate_psychrometric_values(state).get('t_dp')


def p_sat_value_fn(state, _ch: NotifiableCharacteristic):
    return calculate_psychrometric_values(state).get('p_sat')


def p_vap_value_fn(state, _ch: NotifiableCharacteristic):
    return calculate_psychrometric_values(state).get('p_vap')


def hr_value_fn(state, _ch: NotifiableCharacteristic):
    return calculate_psychrometric_values(state).get('hr')


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
            p_sat=self.derived_gauge(
                triggered_by={'temperature', 'pressure', 'humidity'},
                value_fn=p_sat_value_fn,
                metric_name='p_sat', documentation='Saturation Pressure', unit='pa',
            ),
            p_vap=self.derived_gauge(
                triggered_by={'temperature', 'pressure', 'humidity'},
                value_fn=p_vap_value_fn,
                metric_name='p_vap', documentation='Vapor Pressure', unit='pa',
            ),
            hr=self.derived_gauge(
                triggered_by={'temperature', 'pressure', 'humidity'},
                value_fn=hr_value_fn,
                metric_name='hr', documentation='Humidity Ratio', unit='kg_kg',
            ),
            t_wb=self.derived_gauge(
                triggered_by={'temperature', 'pressure', 'humidity'},
                value_fn=t_wb_value_fn,
                metric_name='t_wb', documentation='Wet Bulb Temperature', unit='degrees_celsius',
            ),
            t_dp=self.derived_gauge(
                triggered_by={'temperature', 'pressure', 'humidity'},
                value_fn=t_dp_value_fn,
                metric_name='t_dp', documentation='Dew Point Temperature', unit='degrees_celsius',
            ),
            enthalpy=self.derived_gauge(
                triggered_by={'temperature', 'pressure', 'humidity'},
                value_fn=enthalpy_value_fn,
                metric_name='enthalpy', documentation='Enthalpy', unit='joule',
            )
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
