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


## Two-Stage SemVer Migration: Inverting Defaults while Preserving Dual-Keyword Deprecation Flags
- **Last Updated**: `2026-11-26T15:42:00Z`
- **The Issue**: Transitioning API serialization outputs from deprecated legacy keys (`properties`/`attributes`) to modern semantic keys (`device_info`/`telemetry`) in a minor version bump (v0.2.0) without breaking downstream consumers (like Home Assistant Core diagnostics snapshots) during multi-repository staged rollouts.
- **The Gotcha**:
  1. Downstream consumers bumping dependencies in initial PRs cannot immediately refactor all their internal diagnostic tests and snapshots in the same commit.
  2. Callers frequently confuse or shorten migration argument names (e.g., calling `legacy=True` instead of `legacy_format=True`). If only one keyword name is supported, downstream code breaks with `TypeError: unexpected keyword argument`.
  3. Propagating `is_legacy` through nested helper calls (`client.to_dict` calling `state.to_dict` or `to_json` calling `to_dict`) causes duplicate `DeprecationWarning` emissions and corrupts `stacklevel=2`, making warnings point to internal library frames rather than downstream user code.
  4. Silent precedence (e.g. `legacy=False, legacy_format=True`) can cause subtle bugs unless contradictory combinations are explicitly rejected.
- **The Solution**:
  1. Default both migration keyword arguments to `None` (`legacy_format: bool | None = None, legacy: bool | None = None`) so modern semantic keys are returned by default while distinguishing omitted arguments from explicit `False`.
  2. Implement a single shared resolver (`_resolve_legacy_format`) with contradiction validation:
     ```python
     if legacy is not None and legacy_format is not None and legacy != legacy_format:
         raise ValueError(
             "Conflicting arguments: 'legacy' and 'legacy_format' cannot have different values."
         )
     is_legacy = bool(
         legacy
         if legacy is not None
         else (legacy_format if legacy_format is not None else False)
     )
     ```
  3. Separate public entry points (`to_dict`, `to_json`) that delegate to `_resolve_legacy_format(..., stacklevel=3)` from private data extraction helpers (`_to_dict_data`) that never emit warnings.
  4. Verify with `warnings.catch_warnings(record=True)` asserting `len(recorded) == 1`, `recorded[0].filename == __file__`, and 0 warnings on modern calls.

