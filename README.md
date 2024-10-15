# py-palazzetti-api
A Python library to access and control a Palazzetti stove through a Palazzetti Connection Box.

## Getting started
```python
import asyncio

from pypalazzetti.client import PalazzettiClient


async def main():
    client = PalazzettiClient("192.168.1.2")
    print(f"Connection: {await client.connect()}")
    print(f"Check if online: {await client.is_online()}")
    print(f"Update: {await client.update_state()}")
    print(f"MAC address: {client.mac}")
    print(f"Name: {client.name}")
    print(f"Room temperature: {client.room_temperature}")
    print(f"Target temperature: {client.target_temperature}")
    print(f"Status: {client.status}")
    print(f"Set target temperature: {await client.set_target_temperature(22)}")
    print(f"Target temperature: {client.target_temperature}")
    print(f"Set fan speed: {await client.set_fan_auto()}")
    print(f"Fan speed: {client.fan_speed}")


asyncio.new_event_loop().run_until_complete(main())
```
