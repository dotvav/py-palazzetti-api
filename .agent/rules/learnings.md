# Technical Learnings & Gotchas

## aiohttp Timeout Handling & ESP32 Microcontroller UART Starvation
- **Last Updated**: `2026-11-02T14:11:15Z`
- **The Issue**: In Home Assistant integrations interfacing with embedded IoT bridges (such as the Palazzetti ConnBox ESP32/Lua bridge), entities become unavailable for extended periods (10+ minutes) when network or device latency increases.
- **The Gotcha**:
  1. `aiohttp.ClientSession` defaults to a 300-second (5 minutes) total timeout. Furthermore, `asyncio.TimeoutError` / builtin `TimeoutError` is NOT a subclass of `aiohttp.ClientError`. Handlers catching only `aiohttp.ClientError` miss request timeouts entirely, letting requests hang for up to 300s and blocking `DataUpdateCoordinator` locks.
  2. Conflating static device capabilities (`GET STDT`) with dynamic polling (`GET ALLS`) under a single `self.connected` flag causes any transient polling timeout to invalidate the connection. On the subsequent polling interval, the client sends `connect()` (`GET STDT`) immediately followed by `update_state()` (`GET ALLS`). This back-to-back double request overloads the ESP32's slow UART serial bus (9600 baud) to the stove motherboard, creating a self-sustaining retry storm.
- **The Solution**:
  1. Enforce a sensible request timeout (e.g. 10s) and explicitly catch `TimeoutError`.
  2. Track static capabilities (`_has_properties`) separately from dynamic reachability (`connected`). Once initialized, transient poll failures should only retry dynamic state queries (`GET ALLS`), never re-fetching static hardware definitions.
  3. Enforce an `asyncio.Lock` to strictly serialize concurrent requests on the single-threaded embedded Lua/serial interface.

```python
# pypalazzetti/client.py
async def update_state(self) -> bool:
    if not self._has_properties and not await self.connect():
        return False
    self.connected = (await self._execute_command(command=COMMAND_UPDATE_STATE)).success
    return self.connected
```


## Embedded UART Latency & Timeout String Formatting in Python 3.14/asyncio
- **Last Updated**: `2026-11-12T13:39:00Z`
- **The Issue**: A strict 10s timeout on embedded serial devices (such as Palazzetti ConnBox over 9600 baud UART) causes intermittent `UpdateFailed` and entity unavailability in Home Assistant despite wired Ethernet connectivity. Furthermore, logging `TimeoutError` as `f"API request timed out: {ex}"` produces an empty error message `"API request timed out: "` because Python's built-in `TimeoutError()` instantiated without an argument evaluates to an empty string.
- **The Gotcha**:
  1. Serial status queries (`GET ALLS`) on microcontrollers interacting with stove motherboards can take up to 17-18 seconds under normal operation (especially during active heating or ignition cycles when the microcontroller is busy). An arbitrary 10s timeout creates false positive disconnects.
  2. Built-in `asyncio.TimeoutError` raised by `aiohttp.ClientTimeout` does not supply a default error string (`str(ex) == ""`). Relying on `{ex}` in error formatting masks the actual timeout threshold from the user logs.
- **The Solution**:
  1. Set the default `request_timeout` to at least 25.0s, which accommodates the 18s upper-bound serial latency while remaining well below Home Assistant's 60s coordinator polling interval.
  2. Format the exception explicitly: `f"API request timed out after {self._config.request_timeout}s"`.
