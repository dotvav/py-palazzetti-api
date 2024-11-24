"""Palazzetti data parsing and logic."""

from .const import OFF_STATUSES, HEATING_STATUSES, TEMPERATURE_PROBES
from .temperature import TemperatureDefinition, TemperatureDescriptionKey
import json


class _PalazzettiAPIData(dict[str, bool | dict[str, str | int | float]]):
    """Palazzetti API Data."""

    def __init__(self, payload: str):
        super().__init__(json.loads(payload))
        pass

    @property
    def success(self):
        return "SUCCESS" in self and self["SUCCESS"]


class _PalazzettiState:
    _properties: dict[str, str | int | float] = {}  # Static data
    _attributes: dict[str, str | int | float] = {}  # Mostly sensors data

    def merge_properties(self, state_data: _PalazzettiAPIData) -> bool:
        """Updates the current properties."""
        if state_data.success:
            self._properties = self._properties | state_data["DATA"]
            return True
        return False

    def merge_state(self, state_data: _PalazzettiAPIData) -> bool:
        """Updates the attributes."""
        if state_data.success:
            self._attributes = self._attributes | state_data["DATA"]
            return True
        return False

    def _compare_versions(v1: str, v2: str):
        v1_tokens = v1.split(".")
        v2_tokens = v2.split(".")
        for token1, token2 in zip(v1_tokens, v2_tokens):
            if token1 != token2:
                return int(token1) - int(token2)
        return len(v1_tokens) - len(v2_tokens)

    @property
    def has_power_regulation(self) -> bool:
        return self._properties["STOVETYPE"] != 8

    @property
    def has_ecostart(self) -> bool:
        return self.compare_versions(self._properties["SYSTEM"], "2.1.1") > 0

    @property
    def has_time_synchronization(self) -> bool:
        return self.compare_versions(self._properties["SYSTEM"], "10000.0.0") > 0

    @property
    def has_chrono(self) -> bool:
        return self._properties["CHRONOTYPE"] > 1

    @property
    def has_target_temperature(self) -> bool:
        return self._attributes["SETP"] != 0

    @property
    def has_on_off_switch(self) -> bool:
        return self._properties["STOVETYPE"] not in [7, 8] and self._attributes[
            "LSTATUS"
        ] in [0, 1, 6, 7, 9, 11, 12, 51, 501, 504, 505, 506, 507]

    @property
    def has_error(self) -> bool:
        return self._attributes["LSTATUS"] >= 1000

    @property
    def has_switch_on_multifire_pellet(self) -> bool:
        return self._properties["STOVETYPE"] in [3, 4]

    @property
    def is_air(self) -> bool:
        return self._properties["STOVETYPE"] in [1, 3, 5, 7, 8]

    @property
    def is_hydro(self) -> bool:
        return self._properties["STOVETYPE"] in [2, 4, 6]

    @property
    def has_fan(self) -> bool:
        return self._properties["FAN2TYPE"] > 1

    @property
    def is_first_fan_on(self) -> bool:
        return self._attributes["F2LF"]

    @property
    def has_fan_mode_silent(self) -> bool:
        return self._properties["FAN2TYPE"] > 2

    @property
    def has_fan_mode_auto(self) -> bool:
        return self._properties["FAN2MODE"] in [2, 3]

    @property
    def has_fan_mode_high(self) -> bool:
        return self._properties["FAN2MODE"] == 3

    @property
    def has_fan_mode_prop(self) -> bool:
        return self._properties["FAN2MODE"] == 4

    @property
    def has_main_fan(self) -> bool:
        return self._properties["FAN2TYPE"] > 1

    @property
    def has_second_fan(self) -> bool:
        return self._properties["FAN2TYPE"] > 2

    @property
    def has_third_fan(self) -> bool:
        return self._properties["FAN2TYPE"] > 3

    @property
    def has_leveltronic_pellet_sensor(self) -> bool:
        return self._properties["PSENSTYPE"] == 1

    @property
    def has_capacitive_pellet_sensor(self) -> bool:
        return self._properties["PSENSTYPE"] == 2

    @property
    def pellet_level_min(self) -> float:
        return self._properties["PSENSLMIN"]

    @property
    def pellet_level_max(self) -> float:
        return self._properties["PSENSLMAX"]

    @property
    def pellet_level_threshold(self) -> float:
        return self._properties["PSENSLTSH"]

    @property
    def pellet_level(self) -> float:
        return self._attributes["PLEVEL"]

    @property
    def has_wood_combustion_temperature(self) -> bool:
        return self._properties["STOVETYPE"] in [7, 8]

    @property
    def has_air_outlet_temperature(self) -> bool:
        return (
            self._properties["STOVETYPE"] in [7, 8] and self._properties["FAN2TYPE"] > 1
        )

    @property
    def has_door_control(self) -> bool:
        return self._properties["DOORMOTOR"] == 1

    @property
    def has_light_control(self) -> bool:
        return self._properties["LIGHTCONT"] == 1

    @property
    def product_type(self) -> int:
        return self._properties["STOVETYPE"]

    @property
    def is_product_on(self) -> bool:
        return self._attributes["STATUS"] not in [0, 1]

    @property
    def hydro_t1_temperature(self) -> float:
        return self._attributes["T1"]

    @property
    def hydro_t2_temperature(self) -> float:
        return self._attributes["T2"]

    @property
    def wood_combustion_temperature(self) -> float:
        return self._attributes["T3"]

    @property
    def air_outlet_temperature(self) -> float:
        return self._attributes["T4"]

    def _main_temperature_probe_index(self) -> int:
        if self.is_hydro:
            if self._properties["UICONFIG"] == 1:
                return 1  # T2
            elif self._properties["UICONFIG"] == 10:
                return 4  # T5
        return int(self._properties["MAINTPROBE"])

    def _main_temperature_description(self) -> TemperatureDescriptionKey:
        if self.is_hydro:
            if self._properties["UICONFIG"] == 1:
                return TemperatureDescriptionKey.RETURN_WATER_TEMP
            elif self._properties["UICONFIG"] in [3, 4]:
                return TemperatureDescriptionKey.TANK_WATER_TEMP
        return TemperatureDescriptionKey.ROOM_TEMP

    @property
    def current_temperature(self) -> float:
        return self._attributes[
            TEMPERATURE_PROBES[self._main_temperature_probe_index()]
        ]

    @property
    def T1(self) -> float:
        return self._attributes["T1"]

    @property
    def T2(self) -> float:
        return self._attributes["T2"]

    @property
    def T3(self) -> float:
        return self._attributes["T3"]

    @property
    def T4(self) -> float:
        return self._attributes["T4"]

    @property
    def T5(self) -> float:
        return self._attributes["T5"]

    @property
    def power_mode(self) -> float:
        return self._attributes["PWR"]

    @property
    def target_temperature_min(self) -> int:
        return self._properties["SPLMIN"]

    @property
    def target_temperature_max(self) -> int:
        return self._properties["SPLMAX"]

    @property
    def target_temperature(self) -> int:
        return self._attributes["SETP"]

    @property
    def main_fan_speed(self) -> int:
        return self._attributes["F2L"]

    @property
    def second_fan_speed(self) -> int:
        return self._attributes["F3L"]

    @property
    def third_fan_speed(self) -> int:
        return self._attributes["F4L"]

    @property
    def main_fan_min(self) -> int:
        return self._attributes["FANLMINMAX"][0]

    @property
    def main_fan_max(self) -> int:
        return self._attributes["FANLMINMAX"][1]

    @property
    def second_fan_min(self) -> int:
        return self._attributes["FANLMINMAX"][2]

    @property
    def second_fan_max(self) -> int:
        return self._attributes["FANLMINMAX"][3]

    @property
    def thirdfan_min(self) -> int:
        return self._attributes["FANLMINMAX"][4]

    @property
    def third_fan_max(self) -> int:
        return self._attributes["FANLMINMAX"][5]

    @property
    def door_status(self) -> int:
        return self._attributes["DOOR"]

    @property
    def light_status(self) -> int:
        return self._attributes["LIGHT"]

    @property
    def status(self) -> int:
        return self._attributes["LSTATUS"]

    @property
    def mac(self) -> str:
        return self._properties["MAC"]

    @property
    def name(self) -> str:
        return self._properties["LABEL"]

    @property
    def pellet_quantity(self) -> int:
        return self._attributes["PQT"]

    @property
    def is_on(self) -> bool:
        return self._attributes["LSTATUS"] not in OFF_STATUSES

    @property
    def is_heating(self) -> bool:
        return self._attributes["LSTATUS"] in HEATING_STATUSES

    @property
    def sw_version(self) -> str:
        return self._properties["plzbridge"]

    @property
    def hw_version(self) -> str:
        return self._properties["SYSTEM"]

    def list_temperatures(self) -> TemperatureDefinition:
        """Return a list of temperature sensor definitions"""

        result: list[TemperatureDefinition] = []

        result.append(
            TemperatureDefinition(
                state_property=TEMPERATURE_PROBES[self._main_temperature_probe_index()],
                description_key=self._main_temperature_description(),
            )
        )

        if self.has_air_outlet_temperature or self.air_outlet_temperature != 0:
            result.append(
                TemperatureDefinition(
                    state_property="T4",
                    description_key=TemperatureDescriptionKey.AIR_OUTLET_TEMP,
                )
            )

        if (
            self.has_wood_combustion_temperature
            or self.wood_combustion_temperature != 0
        ):
            result.append(
                TemperatureDefinition(
                    state_property="T3",
                    description_key=TemperatureDescriptionKey.WOOD_COMBUSTION_TEMP,
                )
            )

        if self.is_hydro:
            result.append(
                TemperatureDefinition(
                    state_property="T1",
                    description_key=TemperatureDescriptionKey.T1_HYDRO_TEMP,
                ),
                TemperatureDefinition(
                    state_property="T2",
                    description_key=TemperatureDescriptionKey.T2_HYDRO_TEMP,
                ),
            )

        return result

    def to_dict(
        self,
    ) -> dict[str, bool | dict[str, str | bool | int | float | list[int | str]]]:
        """Return a snapshot of the state."""
        return {
            "properties": self._properties.copy(),
            "attributes": self._attributes.copy(),
        }
