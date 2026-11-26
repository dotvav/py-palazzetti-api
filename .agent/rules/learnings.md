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


## Deprecating Internal IoT State Models with Keyword-Only API Migration
- **Last Updated**: `2026-11-26T12:53:30Z`
- **The Issue**: Refactoring internal state containers (e.g. renaming `properties`/`attributes` to semantic `device_info`/`telemetry`) risks breaking diagnostic serialization (`to_dict()`) and downstream consumers like Home Assistant coordinators, while duplicating dictionary keys in serialization outputs doubles memory allocation.
- **The Gotcha**:
  1. Passing boolean flags positionally (`client.to_dict(False, True)`) creates unreadable client code and fragile signatures.
  2. Typing IoT dictionary payloads strictly as `dict[str, str | int | float]` causes static type checking (`mypy`) failures when raw microcontroller responses contain arrays (e.g., `FANLMINMAX: [0, 5, 0, 1, 0, 1]`, `DNS: [...]`).
  3. Syrupy snapshot tests serialize public object attributes dynamically; private property aliases (`@property def _properties(self)`) maintain complete backward compatibility without polluting snapshot outputs.
- **The Solution**:
  1. Use keyword-only arguments (`*, legacy_format: bool = True`) in `to_dict()` and `to_json()` to maintain legacy key structure by default while allowing callers to opt into modern semantic keys without memory duplication.
  2. Provide `@property` aliases for private attributes and method aliases emitting `DeprecationWarning` with `stacklevel=2`.


## Clean SemVer Breaking Transition: Removing Legacy Serialization Flags (YAGNI)
- **Last Updated**: `2026-11-26T15:50:00Z`
- **The Issue**: Maintaining speculative backward-compatibility keyword arguments (`legacy_format`, `legacy`) in serialization helpers (`to_dict()`, `to_json()`) across SemVer bumps introduces significant maintenance overhead, warning stacklevel complexities, and dead argument resolution paths.
- **The Gotcha**:
  1. Downstream consumers (such as Home Assistant Core `diagnostics.py`) often already invoke parameterless serialization calls like `client.to_dict(redact=True)`.
  2. Trying to bridge serialization schemas through transitional flags in minor/major bumps (v0.2.0) creates unneeded abstraction layers (`_resolve_legacy_format`, `_to_dict_data`) when downstream consumers can simply update their test snapshots in the bump PR.
- **The Solution**:
  1. Apply YAGNI: completely delete transitional compatibility flags (`legacy`, `legacy_format`) and intermediate helpers in the breaking release (v0.2.0).
  2. Keep public signatures minimal: `def to_dict(self, redact: bool = False) -> dict[str, Any]:` and `def to_json(self, redact: bool = False) -> str:`.
  3. Ensure downstream test suites update their mocks and snapshots directly during the dependency bump.

