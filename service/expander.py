import asyncio
from asyncio import Future
from dataclasses import dataclass
from typing import Optional

from bleak import BleakGATTCharacteristic
from loguru import logger

from characteristic.notifiable_characteristic import NotifiableCharacteristic
from service.abstract_service import AbstractService
from service.state import ServiceState

import nest_asyncio

DATA_BUNDLE_UUID = "0000a001-0000-1000-8000-00805f9b34fb"
MISO_UUID = "0000a002-0000-1000-8000-00805f9b34fb"
CS_UUID = "0000a003-0000-1000-8000-00805f9b34fb"
LOCK_UUID = "0000a004-0000-1000-8000-00805f9b34fb"
POWER_UUID = "0000a005-0000-1000-8000-00805f9b34fb"
RESULT_UUID = "0000a006-0000-1000-8000-00805f9b34fb"

ID_MAP = {
    uuid: value for uuid, value in zip(
        [
            DATA_BUNDLE_UUID,
            CS_UUID,
            LOCK_UUID,
            POWER_UUID,
            RESULT_UUID,
        ],
        range(1, 10)
    )
}

# class ExpanderError(Exception):
#     @stat

ID_NAME_MAP = {
    1: 'DATA_BUNDLE',
    2: 'CS',
    3: 'COMMAND',
    4: 'LOCK',
    6: 'POWER',
    7: 'SIZE',
    8: 'ADDRESS',
}

nest_asyncio.apply()


def log_runtime(func):
    from functools import wraps
    import time

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        value = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f'Finished {func.__name__!r} in {end - start:.4f} secs')
        return value

    return wrapper


def log_runtime_async(func):
    from functools import wraps
    import time

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        value = await func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f'Finished {func.__name__!r} in {end - start:.4f} secs')
        return value

    return wrapper


class ExpanderError(Exception):
    def __init__(self, command_id: int):
        command_name = ID_NAME_MAP.get(command_id, 'UNKNOWN')
        super().__init__(f'Command {command_name} failed')


@dataclass
class NoopState(ServiceState):
    def post_process(self, nch_name: str, notifiable_characteristic: NotifiableCharacteristic):
        pass


class LockingContext:
    def __init__(self, service: 'ExpanderService', lock_type: int):
        self.service = service
        self.lock_type = lock_type

    async def __aenter__(self):
        await self.service.set_lock(self.lock_type)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.service.set_lock(0)
        except Exception as e:
            logger.error(f'Failed to release lock: {e}')


class WaitingContext:
    def __init__(self, service: 'ExpanderService', uuid: str):
        self.service = service
        self.characteristic = self.service.service.get_characteristic(uuid)
        if self.characteristic is None:
            raise ValueError(f'Characteristic {uuid} not found')

        self.command_id = ID_MAP[uuid.lower()]

    async def __aenter__(self):
        self.service.future_map[self.command_id] = asyncio.get_running_loop().create_future()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f'Exception in WaitingContext: {exc_type} {exc_val} {exc_tb}')
            return

        fut = self.service.future_map[self.command_id]
        if fut is None:
            logger.error(
                f'Failed to find future for command: {self.command_id}; existing futures: {self.service.future_map}')
            return

        try:
            await fut
        finally:
            _ = self.service.future_map.pop(self.command_id)


class ExpanderService(AbstractService):
    namespace = None
    subsystem = None
    state: NoopState
    cs: int = 0
    address: int = -1
    future_map: dict[id, Future] = {}
    lock_timeout: float = 15.0
    power_wait: int = 1
    cs_wait: int = 1

    def init_state(self):
        self.state = NoopState()

    def pack_data_bundle(
            self,
            lock: Optional[int] = None,
            power: Optional[bool] = None,
            cs: Optional[int] = None,
            command: Optional[int] = None,
            address: Optional[int] = None,
            size_read: int = 0,
            size_write: int = 0,
            mosi: Optional[bytearray] = None,
            power_wait: int = 0,
            cs_wait: int = 0,
    ):
        """
        First byte is control bits:
        [lock_set, power_set, cs_set, command_set, address_set, size_read_set, size_write_set, mosi_set]
        Second byte: reserved
        [
            [0] control_bits,
            [1] reserved_control_bits,
            [2] lock_type,
            [3] power_on_off,
            [4] power_wait,
            [5] cs,
            [6] cs_wait,
            [7] command,
            [8] address,
            [9,10] [size_read, size_read],
            [11, 12] [size_write, size_write],
            [13] reserved,
            [14] reserved,
            [15] reserved,
            ..mosi
        ]
        """
        control_bits = 0
        if lock is not None:
            control_bits |= 1 << 7
        if power is not None:
            control_bits |= 1 << 6
        if cs is not None:
            control_bits |= 1 << 5
        if command is not None:
            control_bits |= 1 << 4
        if address is not None:
            control_bits |= 1 << 3
        control_bits |= 1 << 2
        control_bits |= 1 << 1
        if mosi is not None:
            control_bits |= 1 << 0

        data = bytearray(16)
        data[0] = control_bits
        if lock is not None:
            data[2] = lock

        if power is not None:
            data[3] = 1 if power else 0
        data[4] = power_wait

        if cs is not None:
            data[5] = cs
        data[6] = cs_wait

        if command is not None:
            data[7] = command
        if address is not None:
            data[8] = address
        if size_read is not None:
            data[9] = size_read & 0xFF
            data[10] = (size_read >> 8) & 0xFF
        if size_write is not None:
            data[11] = size_write & 0xFF
            data[12] = (size_write >> 8) & 0xFF
        if mosi is not None:
            data[16:] = mosi

        return data

    @log_runtime_async
    async def set_bundle(self, data: bytearray):
        async with WaitingContext(self, DATA_BUNDLE_UUID) as ctx:
            await self.client.write_gatt_char(ctx.characteristic, data, response=False)

    @log_runtime_async
    async def read_miso(self):
        ch = self.service.get_characteristic(MISO_UUID)
        return await self.client.read_gatt_char(ch, response=False)

    @log_runtime_async
    async def set_cs(self, cs: int):
        async with WaitingContext(self, CS_UUID) as ctx:
            data = cs.to_bytes(1, 'little', signed=False)
            await self.client.write_gatt_char(ctx.characteristic, data, response=False)

    @log_runtime_async
    async def set_lock(self, lock_type: int):
        async with WaitingContext(self, LOCK_UUID) as ctx:
            data = lock_type.to_bytes(1, 'little', signed=False)
            await self.client.write_gatt_char(ctx.characteristic, data, response=False)

    @log_runtime_async
    async def set_power(self, on: bool):
        async with WaitingContext(self, POWER_UUID) as ctx:
            data = on.to_bytes(1, 'little', signed=False)
            await self.client.write_gatt_char(ctx.characteristic, data, response=False)

    async def subscribe(self):
        ch = self.service.get_characteristic(RESULT_UUID)
        await self.client.start_notify(ch, self.wait_response)

    def wait_response(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        result = int.from_bytes(data, byteorder='little', signed=True)
        if result < -100:
            command_id = result + 128
        elif result < 0:
            command_id = -result
        else:
            command_id = result

        is_success = result >= 0
        future = self.future_map.get(command_id)
        if future is None:
            logger.error(f'Failed to find future for command: {command_id}; existing futures: {self.future_map}')
            for fut in self.future_map.values():
                fut.set_exception(ValueError(f'Failed to find future for command: {command_id}'))
            return

        if is_success:
            future.set_result(True)
            return

        future.set_exception(ExpanderError(command_id))

    @log_runtime
    def xfer(self, buf: bytearray, *args, **kwargs):
        """
        0x00 => Ok(Command::Write),
        0x01 => Ok(Command::Read),
        0x02 => Ok(Command::Transfer),
        """

        @with_timeout(self.lock_timeout)
        async def f():
            bundle = self.pack_data_bundle(
                lock=1, power=True, command=2, size_write=len(buf), mosi=buf,
                power_wait=self.power_wait
            )
            await self.set_bundle(bundle)
            return await self.read_miso()

        loop = asyncio.get_running_loop()
        task = loop.create_task(f())
        return loop.run_until_complete(task)

    @log_runtime
    def scan_i2c(self):
        @with_timeout(self.lock_timeout)
        async def f():
            bundle = self.pack_data_bundle(
                lock=2, power=True, command=3, address=0, size_write=0, mosi=bytearray(),
                power_wait=self.power_wait
            )
            await self.set_bundle(bundle)
            return [address for address in await self.read_miso() if address != 0]

        loop = asyncio.get_running_loop()
        task = loop.create_task(f())

        return loop.run_until_complete(task)

    @log_runtime
    def write(self, address: int, buf: bytearray):
        @with_timeout(self.lock_timeout)
        async def f():
            bundle = self.pack_data_bundle(
                lock=2, power=True, command=0, address=address, size_write=len(buf), mosi=buf,
                power_wait=self.power_wait
            )
            await self.set_bundle(bundle)

        loop = asyncio.get_running_loop()
        task = loop.create_task(f())

        return loop.run_until_complete(task)

    @log_runtime
    def read(self, address: int, size: int):
        @with_timeout(self.lock_timeout)
        async def f():
            bundle = self.pack_data_bundle(
                lock=2, power=True, command=1, address=address, size_read=size
            )
            await self.set_bundle(bundle)
            result = await self.read_miso()
            return result[:size]

        loop = asyncio.get_running_loop()
        task = loop.create_task(f())

        return loop.run_until_complete(task)

    @log_runtime
    def write_read(self, address: int, buf: bytearray, size_read: int):
        @with_timeout(self.lock_timeout)
        async def f():
            bundle = self.pack_data_bundle(
                lock=2, power=True, command=2, address=address, size_write=len(buf), size_read=size_read, mosi=buf)
            await self.set_bundle(bundle)
            return await self.read_miso()

        loop = asyncio.get_running_loop()
        task = loop.create_task(f())

        return loop.run_until_complete(task)

    def i2c_rdwr(self, *messages):
        for message in messages:
            match message:
                case WriteMessage(address, buf):
                    self.write(address, buf)
                    logger.info("Wrote {} bytes to address {}", len(buf), address)
                case ReadMessage(address=address, size=size):
                    result = self.read(address, size)
                    message.buf = result
                    logger.info("Read {} bytes from address {}: {}", size, address, result)


def with_timeout(timeout: float):
    def decorator(f):
        async def wrapper(*args, **kwargs):
            loop = asyncio.get_running_loop()
            task = loop.create_task(f(*args, **kwargs))
            return await asyncio.wait_for(task, timeout=timeout)

        return wrapper

    return decorator


@dataclass
class WriteMessage:
    address: int
    buf: bytearray


@dataclass
class ReadMessage:
    address: int
    size: int
    buf: bytearray = None

    def __iter__(self):
        return iter(self.buf)


class I2cMessage:
    @staticmethod
    def write(address: int, buf: bytearray):
        return WriteMessage(address, buf)

    @staticmethod
    def read(address: int, size: int):
        return ReadMessage(address, size)


i2c_msg = I2cMessage()
