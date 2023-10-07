import asyncio
from dataclasses import dataclass

from loguru import logger

from characteristic.notifiable_characteristic import NotifiableCharacteristic
from contrib.scd import SCD4X
from conv import deserialize_noop
from service.abstract_service import AbstractService
from service.expander import ExpanderService
from service.state import ServiceState


@dataclass
class ScdState(ServiceState):
    co2: NotifiableCharacteristic
    temperature: NotifiableCharacteristic
    humidity: NotifiableCharacteristic


class ScdService(AbstractService):
    namespace = 'sensor_hub'
    subsystem = 'scd41'
    state: ScdState

    def __init__(self, expander_service: ExpanderService, registry, labels):
        self.expander_service = expander_service
        self.registry = registry
        self.labels = labels
        self.label_names = [*self.labels.keys()]
        self.registry = registry
        self.init_state()

    async def subscribe(self):
        def run_measurements():
            scd = SCD4X(self.expander_service, quiet=False)
            scd.start_periodic_measurement()
            co2, temperature, relative_humidity, _ = scd.measure(timeout=15)
            self.state.co2.update_value(co2)
            self.state.temperature.update_value(temperature)
            self.state.humidity.update_value(relative_humidity)

        async def f():
            while True:
                try:
                    run_measurements()
                except Exception as e:
                    logger.error('Failed to read %s: {}' % type(e), e, exc_info=True)
                finally:
                    await self.expander_service.set_lock(False)

                await asyncio.sleep(0)

        asyncio.create_task(f())

    def init_state(self):
        self.state = ScdState(
            co2=self.gauge(
                uuid='00000000-0000-0000-0000-000000000000', deserialize_fn=deserialize_noop,
                metric_name='co2', documentation='CO2', unit='ppm',
            ),
            temperature=self.gauge(
                uuid='00000000-0000-0000-0000-000000000000', deserialize_fn=deserialize_noop,
                metric_name='temperature', documentation='Temperature', unit='degrees_celsius',
            ),
            humidity=self.gauge(
                uuid='00000000-0000-0000-0000-000000000000', deserialize_fn=deserialize_noop,
                metric_name='humidity', documentation='Humidity', unit='percent',
            ),
        )
