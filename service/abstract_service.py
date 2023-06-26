from typing import Optional

from bleak import BleakClient
from bleak.backends.service import BleakGATTService
from loguru import logger
from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.registry import Collector

from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.state import ServiceState


class AbstractService:
    namespace: str
    subsystem: str
    state: ServiceState

    def __init__(
            self,
            client: BleakClient,
            service: BleakGATTService,
            registry: CollectorRegistry,
            namespace: Optional[str] = None,
            subsystem: Optional[str] = None,
            labels: Optional[dict] = None,
    ):
        self.client = client
        self.service = service
        self.registry = registry
        self.namespace = namespace or self.namespace
        self.subsystem = subsystem or self.subsystem
        self.labels = labels or {}
        self.label_names = [*self.labels.keys()]

        self.init_state()

    @property
    def metric_props(self):
        return {
            'namespace': self.namespace,
            'subsystem': self.subsystem,
            'labelnames': self.label_names,
            'registry': None
        }

    def gauge(
            self,
            uuid: str,
            deserialize_fn: callable,
            metric_name: str,
            documentation: str,
            unit: str
    ):
        gauge = Gauge(name=metric_name, documentation=documentation, unit=unit, **self.metric_props)

        return NotifiableCharacteristic(
            uuid=uuid.lower(),
            deserialize_fn=deserialize_fn,
            label_dict=self.labels,
            metric=self.get_or_create_collector(gauge)
        )

    @logger.catch
    def get_or_create_collector(self, collector: Collector):
        try:
            self.registry.register(collector)
            return collector
        except ValueError:
            names = self.registry._get_names(collector)
            for name in names:
                existing = self.registry._names_to_collectors.get(name)
                if existing is None:
                    continue
                if type(existing) != type(collector):
                    raise ValueError(f'Collector {collector} is already registered with a different type')
                return existing

        raise ValueError(f'Could not register collector {collector}')

    def init_state(self):
        raise NotImplementedError()

    async def subscribe(self):
        for ch in self.service.characteristics:
            await self.client.start_notify(ch, self.state.update_characteristic)
            self.registry.collect()

    @property
    def display_name(self):
        return f'{self.namespace}:{self.subsystem}::{self.labels}'
