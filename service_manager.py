from asyncio import sleep

from bleak import BleakClient
from prometheus_client import REGISTRY
from loguru import logger

from service.abstract_service import AbstractService
from service.lis2dh12 import LIS2DH12Service
from service.adc import AdcService
from service.bme_280 import Bme280Service
from service.device_information import DeviceInformationService
from service.veml6040 import VEML6040Service


class ServiceManager:
    SERVICE_CLASS_MAP = {
        '5c853275-723b-4754-a329-969d8bc8121d': AdcService,
        '0000180a-0000-1000-8000-00805f9b34fb': DeviceInformationService,
        '5c853275-723b-4754-a329-969d4bc8121e': Bme280Service,
        '5c853275-823b-4754-a329-969d4bc8121e': LIS2DH12Service,
        '5c853275-923b-4754-a329-969d4bc8121e': VEML6040Service,
    }

    def __init__(self, address: str, labels: dict[str, str]):
        self.address = address
        self.labels = labels
        self.client = BleakClient(self.address)
        self.services: list[AbstractService] = []

    async def subscribe_all(self):
        logger.info(f'Connecting to {self.address}')
        await self.client.connect()
        logger.info(f'Connected to {self.address}')

        for svc in self.client.services:
            service_class = self.SERVICE_CLASS_MAP.get(svc.uuid.lower())
            if service_class is None:
                logger.warning(f'No service class for {svc.uuid}; characteristics: {svc.characteristics}')
                continue

            service = service_class(self.client, svc, REGISTRY, labels=self.labels)
            await service.subscribe()
            logger.info(f'Subscribed to {service.display_name}')
            self.services.append(service)

    async def block(self):
        while self.client.is_connected:
            for service in self.services:
                logger.info(f'Service {service.display_name}: {service.state.display_name}')
            await sleep(10)
        logger.error(f'Disconnected from {self.address}')
