from typing import Optional

from bleak import BleakClient
from bleak.backends.service import BleakGATTService
from loguru import logger
from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.registry import Collector

from characteristic.notifiable_characteristic import NotifiableCharacteristic, DerivedMetric
from service.state import ServiceState

import itertools

COUNTER_ITERATOR = itertools.count()


class AbstractService:
    namespace: str
    subsystem: str
    state: ServiceState

    counter = 0

    def __init__(
            self,
            client: BleakClient,
            service: BleakGATTService,
            registry: CollectorRegistry,
            namespace: Optional[str] = None,
            subsystem: Optional[str] = None,
            labels: Optional[dict] = None,
    ):
        self.counter = next(COUNTER_ITERATOR)
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

    def derived_gauge(
            self,
            triggered_by: set[str],
            value_fn: callable,
            metric_name: str,
            documentation: str,
            unit: str,
            post_process_fn: callable = lambda x: x
    ):
        gauge = Gauge(name=metric_name, documentation=documentation, unit=unit, **self.metric_props)
        return DerivedMetric(
            triggered_by=triggered_by,
            value_fn=value_fn,
            label_dict=self.labels,
            metric=self.get_or_create_collector(gauge),
            post_process_fn=post_process_fn
        )

    def gauge(
            self,
            uuid: str,
            deserialize_fn: callable,
            metric_name: str,
            documentation: str,
            unit: str,
            post_process_fn: callable = lambda x: x
    ):
        gauge = Gauge(name=metric_name, documentation=documentation, unit=unit, **self.metric_props)
        if len(uuid) != 36:
            uuid = f'0000{uuid}-0000-1000-8000-00805f9b34fb'.lower()

        return NotifiableCharacteristic(
            uuid=uuid.lower(),
            deserialize_fn=deserialize_fn,
            label_dict=self.labels,
            metric=self.get_or_create_collector(gauge),
            post_process_fn=post_process_fn
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
        for characteristic in self.service.characteristics:
            if characteristic.uuid.lower() in {'a0e4a2ba-1234-4321-0001-00805f9b34fb',
                                               'a0e4a2ba-1234-4321-0002-00805f9b34fb',
                                               'a0e4a2ba-1234-4321-0003-00805f9b34fb', }:
                continue

            logger.info(
                f'[{self.__class__.__name__}] Subscribing to {characteristic.uuid} {characteristic.description}')
            try:
                await self.client.start_notify(characteristic, self.state.update_characteristic)
            except Exception as e:
                logger.error(f'Failed to subscribe to characteristic {characteristic.uuid}: {e}')

    @property
    def display_name(self):
        return f'{self.namespace}:{self.subsystem}::{self.labels}[{self.counter}]'

    def reset_state_metrics(self):
        self.state.reset_metrics()

    async def set_timeout_ms(self, timeout: int):
        raise NotImplementedError()
