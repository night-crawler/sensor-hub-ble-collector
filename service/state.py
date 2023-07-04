from bleak import BleakGATTCharacteristic
from loguru import logger

from characteristic.notifiable_characteristic import NotifiableCharacteristic, DerivedMetric


class ServiceState:
    @logger.catch
    def update_characteristic(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        nch_name, nch = self._find_notifiable_characteristic(characteristic.uuid)
        if nch is None:
            logger.warning(f'Unknown characteristic {characteristic.uuid}; value: {data}')
            return

        nch.update_value(data)
        self.update_derived_metrics(nch_name, nch)
        self.post_process(nch_name, nch)

    def _find_notifiable_characteristic(self, uuid: str):
        for name, value in self.__dict__.items():
            if not isinstance(value, NotifiableCharacteristic):
                continue

            if value.uuid.lower() == uuid.lower():
                return name, value

        return None, None

    @property
    def display_name(self):
        parts = []
        for name, value in self.__dict__.items():
            if isinstance(value, NotifiableCharacteristic):
                parts.append(value.display_name)
            elif isinstance(value, DerivedMetric):
                parts.append(value.display_name)

        self_name = self.__class__.__name__
        return f'{self_name}({", ".join(parts)})'

    def update_derived_metrics(self, nch_name: str, notifiable_characteristic: NotifiableCharacteristic):
        for name, derived in self.__dict__.items():
            if not isinstance(derived, DerivedMetric):
                continue

            if nch_name not in derived.triggered_by:
                continue

            derived.update_value(self, notifiable_characteristic)

    def post_process(self, nch_name: str, notifiable_characteristic: NotifiableCharacteristic):
        pass

    def reset_metrics(self):
        for name, value in self.__dict__.items():
            if isinstance(value, NotifiableCharacteristic):
                value.reset()
            elif isinstance(value, DerivedMetric):
                value.reset()
