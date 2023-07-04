import asyncio
from typing import Optional

from bleak import BleakScanner
from loguru import logger

from service_manager import ServiceManager


class DeviceManager:
    def __init__(self, labels_by_address: Optional[dict[str, dict[str, str]]] = None):
        self._managers: dict[str, ServiceManager] = {}
        self.device_labels = labels_by_address or {}
        self.lock = asyncio.Lock()

    def _get_or_create_manager(self, address: str) -> ServiceManager:
        manager = self._managers.get(address)
        labels_by_address = self.device_labels.get(address, {})
        if manager is None:
            manager = ServiceManager(address, labels={**labels_by_address, 'device': address})
            logger.info(f'Created manager for {address}')
            self._managers[address] = manager
        return manager

    def remove_manager(self, address: str):
        self._managers.pop(address, None)

    async def discover(self):
        while True:
            devices = await BleakScanner.discover()
            logger.info(f'Discovered {len(devices)} devices')
            for device in devices:
                if device.name != 'Sensor Hub BLE':
                    continue

                if device.address in self._managers:
                    continue

                await self.subscribe(device.address)

    async def subscribe(self, device_address: str):
        async with self.lock:
            try:
                manager = self._get_or_create_manager(device_address)
            except Exception as e:
                logger.exception('Failed to initialize manager: {}', e)
                self.remove_manager(device_address)
                return

            try:
                await manager.subscribe_all()
            except Exception as e:
                logger.exception('Failed to subscribe: {}', e)
                self.remove_manager(device_address)
                return

            async def task():
                try:
                    logger.info('Waiting for device {} to disconnect', device_address)
                    await manager.block()
                except Exception as ex:
                    logger.exception('Exception: {}', ex, exc_info=True)
                logger.error('Disconnected from {}', device_address)
                self.remove_manager(device_address)

                async with self.lock:
                    manager.reset_service_metrics()

            asyncio.create_task(task())
