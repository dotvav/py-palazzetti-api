# Python Palazzetti API
An async Python library to access and control a Palazzetti stove through a Palazzetti Connection Box.

## Getting started
```python
import asyncio

from pypalazzetti.client import PalazzettiClient


async def main():
    client = PalazzettiClient("192.168.1.73")
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
    print(f"Min fan speed: {client.fan_speed_min}")
    print(f"Max fan speed: {client.fan_speed_max}")
    print(f"Set fan speed: {await client.set_fan_auto()}")
    print(f"Fan speed: {client.fan_speed}")
    print("---")
    for temp in client.list_temperatures():
        print(f"{temp.description_key}={temp.value}")
    print("---")
    print(client.to_json())



asyncio.new_event_loop().run_until_complete(main())
```
