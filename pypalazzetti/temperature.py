"""Temperature sensor definition"""

from enum import Enum
from typing import Callable


class TemperatureDescriptionKey(str, Enum):
    """Temperature description key enum."""

    ROOM_TEMP = "room_temperature"
    RETURN_WATER_TEMP = "return_water_temperature"
    TANK_WATER_TEMP = "tank_water_temperature"
    WOOD_COMBUSTION_TEMP = "wood_combustion_temperature"
    AIR_OUTLET_TEMP = "air_outlet_temperature"
    T1_HYDRO_TEMP = "t1_hydro"
    T2_HYDRO_TEMP = "t2_hydro"


class TemperatureDefinition:
    """A temperature sensor"""

    _state_function: Callable[[], float]
    description_key: TemperatureDescriptionKey

    def __init__(
        self,
        state_function: Callable[[], float],
        description_key: TemperatureDescriptionKey,
    ):
        self._state_function = state_function
        self.description_key = description_key

    def value(self) -> float:
        """The value of the sensor"""
        return self._state_function()
