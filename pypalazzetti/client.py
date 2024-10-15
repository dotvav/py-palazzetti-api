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
        """Connects to the device."""
        r = await self._execute_command(
            command=COMMAND_UPDATE_PROPERTIES, merge_state=False
        )
        self._state.merge_properties(r)
        self._connected = r is not None and r["SUCCESS"]
        return self._connected

    async def is_online(self) -> bool:
        """Tests if the device is online."""
        if not self._connected:
            await self.connect()
        r = await self._execute_command(command=COMMAND_CHECK_ONLINE)
        return r is not None and r["SUCCESS"]

    async def update_state(self) -> bool:
        """Updates the device's state."""
        if not self._connected:
            await self.connect()
        if self._connected:
            r = await self._execute_command(command=COMMAND_UPDATE_STATE)
            return r is not None and r["SUCCESS"]
        return False

    @property
    def sw_version(self) -> str:
        """The software version."""
        return self._state.sw_version

    @property
    def hw_version(self) -> str:
        """The hardware version"""
        return self._state.hw_version

    @property
    def has_on_off_switch(self) -> bool:
        return self._state.has_on_off_switch

    @property
    def target_temperature(self) -> int:
        """Returns the target temperature"""
        return self._state.target_temperature

    @property
    def room_temperature(self) -> float:
        """Returns the room temperature."""
        return self._state.room_temperature

    @property
    def outlet_temperature(self) -> float:
        """Returns the outlet temperature."""
        return self._state.outlet_temperature

    @property
    def exhaust_temperature(self) -> float:
        """Returns the exhaust temperature."""
        return self._state.exhaust_temperature

    @property
    def host(self) -> str:
        """Returns the host name or IP address."""
        return self._state.host

    @property
    def mac(self) -> str:
        """Returns the mac address."""
        return self._state.mac

    @property
    def name(self) -> str:
        """Returns the stove's name."""
        return self._state.name

    @property
    def status(self) -> int:
        """Returns the stove's status."""
        return self._state.status

    @property
    def fan_speed(self) -> int:
        """Returns the fan mode."""
        return self._state.main_fan_speed

    @property
    def power_mode(self) -> int:
        """Returns the power mode."""
        return self._state.power_mode

    @property
    def pellet_quantity(self) -> int:
        """Returns the pellet quantity."""
        return self._state.pellet_quantity

    @property
    def is_heating(self) -> bool:
        """Checks if the stove is currently heating."""
        return self._state.is_heating

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
        """Sets the fan to silent mode."""
        return await self.set_fan_speed(0)

    async def set_fan_high(self) -> bool:
        """Sets the fan to high mode."""
        return await self.set_fan_speed(6)

    async def set_fan_auto(self) -> bool:
        """Sets the fan to auto mode."""
        return await self.set_fan_speed(7)

    async def set_fan_speed(self, fan_speed: int) -> bool:
        """Sets the fan speed."""
        if fan_speed == 0 and self._state.has_fan_mode_silent:
            return (await self._execute_command(command=COMMAND_SET_FAN_SILENT))[
                "SUCCESS"
            ]
        if (
            (self._state.main_fan_min <= fan_speed <= self._state.main_fan_max)
            or (fan_speed == 6 and self._state.has_fan_mode_high)
            or (fan_speed == 7 and self._state.has_fan_mode_auto)
        ):
            return (
                await self._execute_command(
                    command=COMMAND_SET_FAN_SPEED, parameter=fan_speed
                )
            )["SUCCESS"]
        raise ValidationError(f"Main fan speed ({fan_speed}) out of range.")

    async def set_power_mode(self, power: int) -> bool:
        """Sets the power mode."""
        if 1 <= power <= 5:
            return (
                await self._execute_command(
                    command=COMMAND_SET_POWER_MODE, parameter=power
                )
            )["SUCCESS"]
        raise ValidationError(f"Power mode ({power}) out of range.")

    async def set_on(self, on: bool) -> bool:
        """Sets the stove on or off."""
        if self._state.has_on_off_switch:
            return (
                await self._execute_command(
                    command=COMMAND_SET_ON if on else COMMAND_SET_OFF
                )
            )["SUCCESS"]
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
