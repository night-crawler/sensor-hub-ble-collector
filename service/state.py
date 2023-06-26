from typing import Optional

from bleak import BleakGATTCharacteristic
from loguru import logger

from characteristic.notifiable_characteristic import NotifiableCharacteristic


class ServiceState:
    @logger.catch
    def update_characteristic(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        nch: Optional[NotifiableCharacteristic] = self._find_notifiable_characteristic(characteristic.uuid)
        if nch is None:
            logger.warning(f'Unknown characteristic {characteristic.uuid}; value: {data}')
            return

        nch.update_value(data)

    def _find_notifiable_characteristic(self, uuid: str) -> Optional[NotifiableCharacteristic]:
        for name, value in self.__dict__.items():
            if not isinstance(value, NotifiableCharacteristic):
                continue

            if value.uuid.lower() == uuid.lower():
                return value

        return None

    @property
    def display_name(self):
        parts = []
        for name, value in self.__dict__.items():
            if not isinstance(value, NotifiableCharacteristic):
                continue

            parts.append(value.display_name)

        self_name = self.__class__.__name__
        return f'{self_name}({", ".join(parts)})'
