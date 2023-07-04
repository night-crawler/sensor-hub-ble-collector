import asyncio

import prometheus_client

from device_manager import DeviceManager


async def main():
    prometheus_client.start_http_server(9090)

    manager = DeviceManager(labels_by_address={
        'E0:7D:CD:67:6E:C1': {
            'room': 'living_room',
            'location': 'table',
            'env': 'testing'
        },
        'E7:FC:FA:14:FB:B9': {
            'room': 'living_room',
            'location': 'random',
            'env': 'testing'
        }
    })
    await manager.discover()


asyncio.run(main())
