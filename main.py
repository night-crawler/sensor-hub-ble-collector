import asyncio
from collections import defaultdict

import prometheus_client
from loguru import logger

from device_manager import DeviceManager


async def main():
    prometheus_client.start_http_server(9090)
    devices = defaultdict(lambda: {
        'room': 'unknown',
        'location': 'unknown',
        'env': 'unknown'
    })

    manager = DeviceManager(labels_by_address=devices)
    asyncio.create_task(manager.discover())
    while True:
        # print("where?")
        # for address, service_manager, expander in manager.get_expanders():
        #     print(address, service_manager, expander)
        #     try:
        #         expander.power_wait = 2
        #         scd = SCD4X(expander, quiet=False)
        #         scd.start_periodic_measurement()
        #         co2, temperature, relative_humidity, _ = scd.measure()
        #         print(f'CO2: {co2} ppm, Temperature: {temperature} C, Humidity: {relative_humidity} %rH')
        #
        #         co2, temperature, relative_humidity, _ = scd.measure()
        #         print(f'CO2: {co2} ppm, Temperature: {temperature} C, Humidity: {relative_humidity} %rH')
        #
        #         co2, temperature, relative_humidity, _ = scd.measure()
        #         print(f'CO2: {co2} ppm, Temperature: {temperature} C, Humidity: {relative_humidity} %rH')
        #         await expander.set_lock(False)
        #         # res = expander.write_read(100, bytearray(range(100)))
        #         # res = res[:100]
        #         # print('!!!!', res)
        #     except Exception as e:
        #         logger.error('Failed to read %s: {}' % type(e), e, exc_info=True)

        await asyncio.sleep(10)


asyncio.run(main())
