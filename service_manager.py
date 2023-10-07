from asyncio import sleep

from bleak import BleakClient
from prometheus_client import REGISTRY
from loguru import logger

from service.abstract_service import AbstractService
from service.lis2dh12 import LIS2DH12Service
from service.adc import AdcService
from service.bme_280 import Bme280Service
from service.device_information import DeviceInformationService
from service.expander import ExpanderService
from service.scd_service import ScdService
from service.veml6040 import VEML6040Service


class ServiceManager:
    SERVICE_CLASS_MAP = {
        '5c853275-723b-4754-a329-969d8bc8121d': AdcService,
        '0000180a-0000-1000-8000-00805f9b34fb': DeviceInformationService,
        '5c853275-723b-4754-a329-969d4bc8121e': Bme280Service,
        '5c853275-823b-4754-a329-969d4bc8121e': LIS2DH12Service,
        '5c853275-923b-4754-a329-969d4bc8121e': VEML6040Service,
        'ac866789-aaaa-eeee-a329-969d4bc8621e': ExpanderService,
    }

    I2C_ADDRESS_SERVICE_MAP = {
        0x62: ScdService
    }

    def __init__(self, address: str, labels: dict[str, str]):
        self.address = address
        self.labels = labels
        self.client = BleakClient(self.address)
        self.services: list[AbstractService] = []

    def get_expander(self) -> ExpanderService | None:
        for service in self.services:
            if isinstance(service, ExpanderService):
                return service

        return None

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

            if isinstance(service, Bme280Service) and self.address == 'D0:C4:28:22:81:9D':
                await service.set_calibration(16.0, 0.0, 0.0)

            if isinstance(service, Bme280Service) and self.address == 'D4:B7:67:56:DC:3B':
                await service.set_calibration(14.0, 0.3, -850.0)

            if isinstance(service, Bme280Service) and self.address == 'FA:6F:EC:EE:4B:36':
                await service.set_calibration(1.0, 0.0, 30.0)

            if isinstance(service, Bme280Service) and self.address == 'D3:67:5D:20:A8:42':
                await service.set_calibration(3.0, 0.0, 140.0)

            if isinstance(service, Bme280Service) and self.address == 'D0:F6:3B:34:4C:1F':
                await service.set_calibration(6.0, 0.0, 0)

            if isinstance(service, ExpanderService):
                try:
                    i2c_addresses = await service.scan_i2c()
                except Exception as e:
                    logger.error(f'Failed to scan i2c: {e}')
                    continue
                finally:
                    await service.set_lock(False)

                # i2c_addresses = [0x62]

                for address in i2c_addresses:
                    logger.success(f'Found i2c device at 0x{address:02x}')
                    i2c_service_class = self.I2C_ADDRESS_SERVICE_MAP.get(address)
                    if i2c_service_class is None:
                        logger.warning(f'No i2c service class for 0x{address:02x}')
                        continue
                    i2c_svc = i2c_service_class(service, REGISTRY, labels=self.labels)
                    await i2c_svc.subscribe()

    async def block(self):
        while self.client.is_connected:
            for service in self.services:
                logger.info(f'Service {service.display_name}: {service.state.display_name}')
            await sleep(10)
        logger.error(f'Disconnected from {self.address}')

    def reset_service_metrics(self):
        for service in self.services:
            service.reset_state_metrics()
