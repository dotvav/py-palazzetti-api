"""Python wrapper for the Palazzetti Connection Box API."""

import asyncio
import json
from json.decoder import JSONDecodeError
from typing import Any

import aiohttp

from .config import PalazzettiClientConfig
from .const import (
    API_COMMAND_URL_TEMPLATE,
    COMMAND_CHECK_ONLINE,
    COMMAND_GET_DEVICE_INFO,
    COMMAND_GET_TELEMETRY,
    COMMAND_SET_DOOR,
    COMMAND_SET_FAN_SILENT,
    COMMAND_SET_LEFT_FAN_SPEED,
    COMMAND_SET_LIGHT,
    COMMAND_SET_MAIN_FAN_SPEED,
    COMMAND_SET_OFF,
    COMMAND_SET_ON,
    COMMAND_SET_POWER_MODE,
    COMMAND_SET_RIGHT_FAN_SPEED,
    COMMAND_SET_TEMPERATURE,
    REDACTED_DATA,
)
from .exceptions import CommunicationError, ValidationError
from .fan import FanType
from .state import _PalazzettiAPIData, _PalazzettiState
from .temperature import TemperatureDefinition


class PalazzettiClient:
    """Interface class for the Palazzetti Connection Box API."""

    connected = False

    def __init__(
        self,
        hostname: str,
        session: aiohttp.ClientSession | None = None,
        config: PalazzettiClientConfig | None = None,
    ):
        self._hostname = hostname
        self._session = session or aiohttp.ClientSession()
        self._config = config or PalazzettiClientConfig()
        self._state = _PalazzettiState(self._config)
        self._has_device_info = False
        self._lock = asyncio.Lock()

    @property
    def _has_properties(self) -> bool:
        """DEPRECATED - Use _has_device_info instead."""
        return self._has_device_info

    @_has_properties.setter
    def _has_properties(self, value: bool) -> None:
        self._has_device_info = value

    async def connect(self) -> bool:
        """Connect to the device."""
        r = await self._execute_command(
            command=COMMAND_GET_DEVICE_INFO,
            merge_state=False,
        )
        if r.success:
            self._state.merge_device_info(r)
            self._has_device_info = True
            self.connected = True
        else:
            self.connected = False
        return self.connected

    async def is_online(self) -> bool:
        """Test if the device is online."""
        if not self._has_device_info:
            await self.connect()
        return (await self._execute_command(command=COMMAND_CHECK_ONLINE)).success

    async def update_state(self) -> bool:
        """Update the device's state."""
        # Connect if not connected yet
        if not self._has_device_info and not await self.connect():
            return False
        # Check if connection was successful before updating
        self.connected = (
            await self._execute_command(command=COMMAND_GET_TELEMETRY)
        ).success
        return self.connected

    async def update_telemetry(self) -> bool:
        """Update the device's telemetry."""
        return await self.update_state()

    @property
    def sw_version(self) -> str:
        """Return the software version."""
        return self._state.sw_version

    @property
    def hw_version(self) -> str:
        """Return the hardware version"""
        return self._state.hw_version

    @property
    def has_on_off_switch(self) -> bool:
        """Return the availability of the on/of switch"""
        return self._state.has_on_off_switch

    @property
    def target_temperature(self) -> int:
        """Return the target temperature"""
        return self._state.target_temperature

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self._state.current_temperature

    @property
    def has_air_outlet_temperature(self) -> bool:
        """Return the air outlet temperature."""
        return self._state.has_air_outlet_temperature

    @property
    def air_outlet_temperature(self) -> float:
        """Return the air outlet temperature."""
        return self._state.air_outlet_temperature

    @property
    def room_temperature(self) -> float:
        """DEPRECATED - Return the room temperature."""
        return self._state.current_temperature

    @property
    def outlet_temperature(self) -> float:
        """DEPRECATED - Return the outlet temperature."""
        return self._state.air_outlet_temperature

    @property
    def has_wood_combustion_temperature(self) -> bool:
        """Return the air outlet temperature."""
        return self._state.has_wood_combustion_temperature

    @property
    def wood_combustion_temperature(self) -> float:
        """Return the wood combustion temperature."""
        return self._state.wood_combustion_temperature

    @property
    def T1(self) -> float:
        """Return the T1 temperature."""
        return self._state.T1

    @property
    def T2(self) -> float:
        """Return the T2 temperature."""
        return self._state.T2

    @property
    def T3(self) -> float:
        """Return the T3 temperature."""
        return self._state.T3

    @property
    def T4(self) -> float:
        """Return the T4 temperature."""
        return self._state.T4

    @property
    def T5(self) -> float:
        """Return the T5 temperature."""
        return self._state.T5

    def list_temperatures(self) -> list[TemperatureDefinition]:
        """Return a list of all available temperatures."""
        return self._state.list_temperatures()

    @property
    def host(self) -> str:
        """Return the host name or IP address."""
        return self._hostname

    @property
    def mac(self) -> str:
        """Return the mac address."""
        return self._state.mac

    @property
    def name(self) -> str:
        """Return the stove's name."""
        return self._state.name

    @property
    def status(self) -> int:
        """Return the stove's status."""
        return self._state.status

    @property
    def fan_speed(self) -> int:
        """DEPRECATED - Return the fan mode."""
        return self._state.main_fan_speed

    def current_fan_speed(self, fan: FanType = FanType.MAIN) -> int:
        """Return a fan's speed"""
        if fan == FanType.MAIN:
            return self._state.main_fan_speed
        elif fan == FanType.LEFT:
            return self._state.left_fan_speed
        elif fan == FanType.RIGHT:
            return self._state.right_fan_speed
        else:
            return 0

    @property
    def power_mode(self) -> int:
        """Return the power mode."""
        return self._state.power_mode

    @property
    def pellet_quantity(self) -> int:
        """Return the pellet quantity."""
        return self._state.pellet_quantity

    @property
    def has_pellet_level(self) -> bool:
        """Return the availability of the pellet level."""
        return (
            self._state.has_leveltronic_pellet_sensor
            or self._state.has_capacitive_pellet_sensor
        )

    @property
    def pellet_level(self) -> float:
        """Return the pellet level."""
        return self._state.pellet_level

    @property
    def pellet_level_min(self) -> float:
        """Return the minimum pellet level."""
        return self._state.pellet_level_min

    @property
    def pellet_level_max(self) -> float:
        """Return the maximum pellet level."""
        return self._state.pellet_level_max

    @property
    def pellet_level_threshold(self) -> float:
        """Return the pellet level threshold."""
        return self._state.pellet_level_threshold

    @property
    def is_on(self) -> bool:
        """Check if the stove is on."""
        return self._state.is_on

    @property
    def is_heating(self) -> bool:
        """Check if the stove is currently heating."""
        return self._state.is_heating

    @property
    def has_light_control(self) -> bool:
        """Check if light control is available."""
        return self._state.has_light_control

    @property
    def light_status(self) -> int:
        """Return the light status."""
        return self._state.light_status

    @property
    def is_light_on(self) -> bool:
        """Check if the light is on."""
        return self._state.light_status == 1

    @property
    def has_door_control(self) -> bool:
        """Check if motorized door control is available."""
        return self._state.has_door_control

    @property
    def door_status(self) -> int:
        """Return the door status."""
        return self._state.door_status

    @property
    def is_door_open(self) -> bool:
        """Check if the door is open."""
        return self._state.door_status != 0

    @property
    def has_fan_silent(self) -> bool:
        """Check if the fan has the silent mode available."""
        return self._state.has_fan_mode_silent

    @property
    def has_fan_high(self) -> bool:
        """Check if the fan has the high mode available."""
        return self._state.has_fan_mode_high

    @property
    def has_fan_auto(self) -> bool:
        """Check if the fan has the auto mode available."""
        return self._state.has_fan_mode_auto

    def has_fan(self, fan: FanType = FanType.MAIN) -> bool:
        """Check if a fan is available"""
        if fan == FanType.MAIN:
            return self._state.has_main_fan
        elif fan == FanType.LEFT:
            return self._state.has_left_fan
        elif fan == FanType.RIGHT:
            return self._state.has_right_fan
        return False

    @property
    def fan_speed_min(self) -> int:
        """DEPRRECATED - Return the minimum fan speed."""
        return self._state.main_fan_min

    @property
    def fan_speed_max(self) -> int:
        """DEPRRECATED - Return the maximum fan speed."""
        return self._state.main_fan_max

    def min_fan_speed(self, fan: FanType = FanType.MAIN) -> int:
        """Return the minimum fan speed."""
        if fan == FanType.MAIN:
            return self._state.main_fan_min
        elif fan == FanType.LEFT:
            return self._state.left_fan_min
        elif fan == FanType.RIGHT:
            return self._state.right_fan_min
        return 0

    def max_fan_speed(self, fan: FanType = FanType.MAIN) -> int:
        """Return the maximum fan speed."""
        if fan == FanType.MAIN:
            return self._state.main_fan_max
        elif fan == FanType.LEFT:
            return self._state.left_fan_max
        elif fan == FanType.RIGHT:
            return self._state.right_fan_max
        return 1

    @property
    def target_temperature_min(self) -> int:
        """Return the minimum target temperature."""
        return self._state.target_temperature_min

    @property
    def target_temperature_max(self) -> int:
        """Return the maximum target temperature."""
        return self._state.target_temperature_max

    async def set_target_temperature(self, temperature: int) -> bool:
        """Sets the target temperature."""
        if (
            temperature >= self._state.target_temperature_min
            and temperature <= self._state.target_temperature_max
        ):
            res = await self._execute_command(
                command=COMMAND_SET_TEMPERATURE,
                parameter=temperature,
            )
            return self._state.merge_telemetry(res)
        return False

    async def set_fan_silent(self) -> bool:
        """Set the fan to silent mode."""
        return (
            await self._execute_command(
                command=COMMAND_SET_FAN_SILENT, merge_state=True
            )
        ).success

    async def set_fan_high(self) -> bool:
        """Set the fan to high mode."""
        return await self.set_fan_speed(6)

    async def set_fan_auto(self) -> bool:
        """Set the fan to auto mode."""
        return await self.set_fan_speed(7)

    async def set_fan_speed(self, fan_speed: int, fan: FanType = FanType.MAIN) -> bool:
        """Set the fan speed."""
        if not self.has_fan(fan):
            raise ValidationError(f'Fan "{fan}" not available.')

        if (
            (self.min_fan_speed(fan) <= fan_speed <= self.max_fan_speed(fan))
            or (
                fan == FanType.MAIN and fan_speed == 6 and self._state.has_fan_mode_high
            )
            or (
                fan == FanType.MAIN and fan_speed == 7 and self._state.has_fan_mode_auto
            )
        ):
            if fan == FanType.LEFT:
                command = COMMAND_SET_LEFT_FAN_SPEED
            elif fan == FanType.RIGHT:
                command = COMMAND_SET_RIGHT_FAN_SPEED
            else:
                command = COMMAND_SET_MAIN_FAN_SPEED

            return (
                await self._execute_command(
                    command=command,
                    parameter=fan_speed,
                    merge_state=True,
                )
            ).success
        raise ValidationError(f'Fan "{fan}" speed ({fan_speed}) out of range.')

    async def set_power_mode(self, power: int) -> bool:
        """Set the power mode."""
        if 1 <= power <= 5:
            return (
                await self._execute_command(
                    command=COMMAND_SET_POWER_MODE,
                    parameter=power,
                )
            ).success
        raise ValidationError(f"Power mode ({power}) out of range.")

    async def set_on(self, on: bool) -> bool:
        """Set the stove on or off."""
        if self._state.has_on_off_switch:
            return (
                await self._execute_command(
                    command=COMMAND_SET_ON if on else COMMAND_SET_OFF,
                )
            ).success
        raise ValidationError("Main operation switch not available.")

    async def set_light(self, on: bool) -> bool:
        """Set the light on or off."""
        if self._state.has_light_control:
            return (
                await self._execute_command(
                    command=COMMAND_SET_LIGHT,
                    parameter=1 if on else 0,
                    merge_state=True,
                )
            ).success
        raise ValidationError("Light control not available.")

    async def set_door(self, open_door: bool) -> bool:
        """Set the door open or closed."""
        if self._state.has_door_control:
            return (
                await self._execute_command(
                    command=COMMAND_SET_DOOR,
                    parameter=1 if open_door else 2,
                    merge_state=True,
                )
            ).success
        raise ValidationError("Door control not available.")

    async def _execute_command(
        self,
        command: str,
        parameter: str | int | None = None,
        merge_state: bool = True,
    ) -> _PalazzettiAPIData:
        request_url = API_COMMAND_URL_TEMPLATE.format(
            host=self._hostname,
            command_and_parameter=f"{command} {parameter}"
            if parameter is not None
            else command,
        )

        timeout = aiohttp.ClientTimeout(total=self._config.request_timeout)

        async with self._lock:
            try:
                async with self._session.get(request_url, timeout=timeout) as response:
                    payload = _PalazzettiAPIData(await response.text())
            except TimeoutError as ex:
                self.connected = False
                raise CommunicationError(
                    f"API request timed out after {self._config.request_timeout}s"
                ) from ex
            except (TypeError, JSONDecodeError) as ex:
                self.connected = False
                raise CommunicationError("Invalid API response") from ex
            except aiohttp.ClientError as ex:
                self.connected = False
                raise CommunicationError("API communication error") from ex

            if merge_state:
                self._state.merge_telemetry(payload)
            return payload

    def to_json(
        self,
        redact: bool = False,
        *,
        legacy_format: bool = True,
    ) -> str:
        """Return a snapshot of the client as a json string."""
        return json.dumps(self.to_dict(redact=redact, legacy_format=legacy_format))

    def to_dict(
        self,
        redact: bool = False,
        *,
        legacy_format: bool = True,
    ) -> dict[str, Any]:
        """Return a snapshot of the client as a dict."""
        info_key = "properties" if legacy_format else "device_info"
        telemetry_key = "attributes" if legacy_format else "telemetry"

        data: dict[str, Any] = {
            "host": self._hostname,
            "connected": self.connected,
            "state": self._state.to_dict(legacy_format=legacy_format),
        }

        if redact:
            redacted = {
                "DNS": [REDACTED_DATA],
                "EADDR": REDACTED_DATA,
                "EGW": REDACTED_DATA,
                "EMAC": REDACTED_DATA,
                "GATEWAY": REDACTED_DATA,
                "MAC": REDACTED_DATA,
                "SN": REDACTED_DATA,
                "WADR": REDACTED_DATA,
                "WBCST": REDACTED_DATA,
                "WMAC": REDACTED_DATA,
                "WGW": REDACTED_DATA,
                "WSSID": REDACTED_DATA,
            }
            data["host"] = REDACTED_DATA
            data["state"][info_key] = data["state"][info_key] | redacted
            data["state"][telemetry_key] = data["state"][telemetry_key] | redacted

        return data
