"""Python wrapper for the Palazzetti Connection Box API."""

from .const import (
    API_COMMAND_URL_TEMPLATE,
    COMMAND_CHECK_ONLINE,
    COMMAND_SET_FAN_SPEED,
    COMMAND_SET_FAN_SILENT,
    COMMAND_SET_OFF,
    COMMAND_SET_ON,
    COMMAND_SET_POWER_MODE,
    COMMAND_SET_TEMPERATURE,
    COMMAND_UPDATE_PROPERTIES,
    COMMAND_UPDATE_STATE,
)
from .state import PalazzettiState
from .exceptions import CommunicationError, ValidationError
import aiohttp
import json
from json.decoder import JSONDecodeError


class PalazzettiClient:
    """Interface class for the Overkiz API."""

    _hostname: str
    _state = PalazzettiState()
    _connected = False

    def __init__(
        self,
        hostname: str,
    ):
        self._hostname = hostname

    async def connect(self) -> bool:
        """Connect to the device."""
        r = await self._execute_command(
            command=COMMAND_UPDATE_PROPERTIES, merge_state=False
        )
        if self._is_success(r):
            self._state.merge_properties(r)
            self._connected = True
            return True
        return False

    async def is_online(self) -> bool:
        """Test if the device is online."""
        if not self._connected:
            await self.connect()
        r = await self._execute_command(command=COMMAND_CHECK_ONLINE)
        return self._is_success(r)

    async def update_state(self) -> bool:
        """Update the device's state."""
        if not self._connected:
            await self.connect()
        if self._connected:
            r = await self._execute_command(command=COMMAND_UPDATE_STATE)
            return self._is_success(r)
        return False

    @property
    def sw_version(self) -> str:
        """Return the software version."""
        return self._state.sw_version

    @property
    def hw_version(self) -> str:
        """return the hardware version"""
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
    def room_temperature(self) -> float:
        """Return the room temperature."""
        return self._state.room_temperature

    @property
    def outlet_temperature(self) -> float:
        """Return the outlet temperature."""
        return self._state.outlet_temperature

    @property
    def exhaust_temperature(self) -> float:
        """Return the exhaust temperature."""
        return self._state.exhaust_temperature

    @property
    def host(self) -> str:
        """Return the host name or IP address."""
        return self._state.host

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
        """Return the fan mode."""
        return self._state.main_fan_speed

    @property
    def power_mode(self) -> int:
        """Return the power mode."""
        return self._state.power_mode

    @property
    def pellet_quantity(self) -> int:
        """Return the pellet quantity."""
        return self._state.pellet_quantity

    @property
    def is_heating(self) -> bool:
        """Check if the stove is currently heating."""
        return self._state.is_heating

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

    @property
    def fan_speed_min(self) -> int:
        """Return the minimum fan speed."""
        # Some devices state 0 as the min, which is equivalent to silent, even when silent mode is not available
        return max(self._state.main_fan_min, 1)

    @property
    def fan_speed_max(self) -> int:
        """Return the maximum fan speed."""
        return self._state.main_fan_max

    async def set_target_temperature(self, temperature: int) -> bool:
        """Sets the target temperature."""
        if (
            temperature >= self._state.target_temperature_min
            and temperature <= self._state.target_temperature_max
        ):
            res = await self._execute_command(
                command=COMMAND_SET_TEMPERATURE, parameter=temperature
            )
            return self._state.merge_state(res)
        return False

    async def set_fan_silent(self) -> bool:
        """Set the fan to silent mode."""
        return await self.set_fan_speed(0)

    async def set_fan_high(self) -> bool:
        """Set the fan to high mode."""
        return await self.set_fan_speed(6)

    async def set_fan_auto(self) -> bool:
        """Set the fan to auto mode."""
        return await self.set_fan_speed(7)

    async def set_fan_speed(self, fan_speed: int) -> bool:
        """Set the fan speed."""
        if fan_speed == 0 and self._state.has_fan_mode_silent:
            return self._is_success(
                await self._execute_command(command=COMMAND_SET_FAN_SILENT)
            )
        if (
            (self._state.main_fan_min <= fan_speed <= self._state.main_fan_max)
            or (fan_speed == 6 and self._state.has_fan_mode_high)
            or (fan_speed == 7 and self._state.has_fan_mode_auto)
        ):
            return self._is_success(
                await self._execute_command(
                    command=COMMAND_SET_FAN_SPEED, parameter=fan_speed
                )
            )
        raise ValidationError(f"Main fan speed ({fan_speed}) out of range.")

    async def set_power_mode(self, power: int) -> bool:
        """Set the power mode."""
        if 1 <= power <= 5:
            return self._is_success(
                await self._execute_command(
                    command=COMMAND_SET_POWER_MODE, parameter=power
                )
            )
        raise ValidationError(f"Power mode ({power}) out of range.")

    async def set_on(self, on: bool) -> bool:
        """Set the stove on or off."""
        if self._state.has_on_off_switch:
            return self._is_success(
                await self._execute_command(
                    command=COMMAND_SET_ON if on else COMMAND_SET_OFF
                )
            )
        raise ValidationError("Main operation switch not available.")

    async def _execute_command(
        self, command: str, parameter: str | int = None, merge_state=True
    ) -> dict[str, bool | dict[str, str | int | float]]:
        request_url = API_COMMAND_URL_TEMPLATE.format(
            host=self._hostname,
            command_and_parameter=f"{command} {parameter}" if parameter else command,
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(request_url) as response:
                    payload = json.loads(await response.text())
        except (TypeError, JSONDecodeError) as ex:
            raise CommunicationError("Invalid API response") from ex
        except aiohttp.ClientError as ex:
            raise CommunicationError("API communication error") from ex

        if merge_state:
            self._state.merge_state(payload)
        return payload

    def _is_success(
        self, payload: dict[str, bool | dict[str, str | int | float]]
    ) -> bool:
        return payload and payload.get("SUCCESS", False)
