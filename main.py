import asyncio
import prometheus_client
from loguru import logger

from service_manager import ServiceManager

# SENSOR_HUB_ADDRESS = 'F4:DB:A5:69:DF:87'
SENSOR_HUB_ADDRESS = 'E0:7D:CD:67:6E:C1'


async def main():
    prometheus_client.start_http_server(9090)

    while True:
        try:
            manager = ServiceManager(SENSOR_HUB_ADDRESS, labels={'room': 'living_room', 'env': 'testing'})
            await manager.subscribe_all()
            await manager.block()
        except Exception as e:
            logger.error(f'Exception: {e}', exc_info=True)
            continue


asyncio.run(main())
