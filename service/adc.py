from dataclasses import dataclass

from conv import deserialize_voltage, deserialize_int
from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.abstract_service import AbstractService
from service.state import ServiceState


@dataclass
class AdcState(ServiceState):
    voltage_0: NotifiableCharacteristic
    voltage_1: NotifiableCharacteristic
    voltage_2: NotifiableCharacteristic
    voltage_3: NotifiableCharacteristic
    voltage_4: NotifiableCharacteristic
    voltage_5: NotifiableCharacteristic
    voltage_6: NotifiableCharacteristic
    sample_count: NotifiableCharacteristic
    elapsed: NotifiableCharacteristic


class AdcService(AbstractService):
    namespace: str = 'sensor_hub'
    subsystem: str = 'nrf_adc'
    state: AdcState

    def init_state(self):
        self.state = AdcState(
            voltage_0=self.gauge(
                uuid='00002b18-0000-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_0', documentation='Voltage on ADC channel 0', unit='volts',
            ),
            voltage_1=self.gauge(
                uuid='00002b18-0001-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_1', documentation='Voltage on ADC channel 1', unit='volts',
            ),
            voltage_2=self.gauge(
                uuid='00002b18-0002-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_2', documentation='Voltage on ADC channel 2', unit='volts',
            ),
            voltage_3=self.gauge(
                uuid='00002b18-0003-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_3', documentation='Voltage on ADC channel 3', unit='volts',
            ),
            voltage_4=self.gauge(
                uuid='00002b18-0004-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_4', documentation='Voltage on ADC channel 4', unit='volts',
            ),
            voltage_5=self.gauge(
                uuid='00002b18-0005-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_5', documentation='Voltage on ADC channel 5', unit='volts',
            ),
            voltage_6=self.gauge(
                uuid='00002b18-0006-1000-8000-00805f9b34fb', deserialize_fn=deserialize_voltage,
                metric_name='voltage_6', documentation='Voltage on ADC channel 6', unit='volts',
            ),
            sample_count=self.gauge(
                uuid='a0e4d2ba-0000-8000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='sample', documentation='Sample count', unit='count',
            ),
            elapsed=self.gauge(
                uuid='a0e4d2ba-0001-8000-0000-00805f9b34fb', deserialize_fn=deserialize_int,
                metric_name='elapsed', documentation='Elapsed us', unit='us',
            ),
        )
