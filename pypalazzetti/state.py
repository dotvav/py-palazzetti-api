"""Palazzetti data parsing and logic."""

import json
import warnings
from typing import Any

from .config import PalazzettiClientConfig
from .const import HEATING_STATUSES, OFF_STATUSES, TEMPERATURE_PROBES
from .temperature import TemperatureDefinition, TemperatureDescriptionKey


class _PalazzettiAPIData(dict[str, Any]):
    """Palazzetti API Data."""

    def __init__(self, payload: str):
        super().__init__(json.loads(payload))

    @property
    def success(self) -> bool:
        return bool(self.get("SUCCESS", False))


class _PalazzettiState:
    _device_info: dict[str, Any]  # Static data
    _telemetry: dict[str, Any]  # Mostly sensors data

    def __init__(self, config: PalazzettiClientConfig):
        self._device_info = {}
        self._telemetry = {}
        self._config = config

    @property
    def _properties(self) -> dict[str, Any]:
        """DEPRECATED - Use _device_info instead."""
        return self._device_info

    @property
    def _attributes(self) -> dict[str, Any]:
        """DEPRECATED - Use _telemetry instead."""
        return self._telemetry

    def merge_device_info(self, state_data: _PalazzettiAPIData) -> bool:
        """Updates the static device information."""
        if state_data.success:
            self._device_info = self._device_info | state_data["DATA"]
            return True
        return False

    def merge_properties(self, state_data: _PalazzettiAPIData) -> bool:
        """DEPRECATED - Use merge_device_info instead."""
        warnings.warn(
            "merge_properties is deprecated and will be removed in a future release. "
            "Use merge_device_info instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.merge_device_info(state_data)

    def merge_telemetry(
        self,
        state_data: _PalazzettiAPIData,
    ) -> bool:
        """Updates the telemetry and attributes."""
        if state_data.success:
            data = state_data["DATA"]
            if "LIGHT" in data and "LGHT" not in data:
                data["LGHT"] = data["LIGHT"]
            if (
                "PQT" in data
                and self._config.pellet_quantity_sanitize
                and "PQT" in self._telemetry
            ):
                data["PQT"] = max(data["PQT"], self._telemetry["PQT"])
            self._telemetry = self._telemetry | data
            return True
        return False

    def merge_state(
        self,
        state_data: _PalazzettiAPIData,
    ) -> bool:
        """DEPRECATED - Use merge_telemetry instead."""
        warnings.warn(
            "merge_state is deprecated and will be removed in a future release. "
            "Use merge_telemetry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.merge_telemetry(state_data)

    def _compare_versions(self, v1: str, v2: str):
        v1_tokens = v1.split(".")
        v2_tokens = v2.split(".")
        for token1, token2 in zip(v1_tokens, v2_tokens):
            if token1 != token2:
                return int(token1) - int(token2)
        return len(v1_tokens) - len(v2_tokens)

    @property
    def has_power_regulation(self) -> bool:
        return self._device_info["STOVETYPE"] != 8

    @property
    def has_ecostart(self) -> bool:
        return self._compare_versions(str(self._device_info["SYSTEM"]), "2.1.1") > 0

    @property
    def has_time_synchronization(self) -> bool:
        return self._compare_versions(str(self._device_info["SYSTEM"]), "10000.0.0") > 0

    @property
    def has_chrono(self) -> bool:
        val = self._device_info.get("CHRONOTYPE")
        return val is not None and int(val) > 1

    @property
    def has_target_temperature(self) -> bool:
        return self._telemetry.get("SETP") != 0

    @property
    def has_on_off_switch(self) -> bool:
        return self._device_info["STOVETYPE"] not in [7, 8] and self._telemetry[
            "LSTATUS"
        ] in [0, 1, 6, 7, 9, 11, 12, 51, 501, 504, 505, 506, 507]

    @property
    def has_error(self) -> bool:
        return int(self._telemetry["LSTATUS"]) >= 1000

    @property
    def has_switch_on_multifire_pellet(self) -> bool:
        return self._device_info["STOVETYPE"] in [3, 4]

    @property
    def is_air(self) -> bool:
        return self._device_info["STOVETYPE"] in [1, 3, 5, 7, 8]

    @property
    def is_hydro(self) -> bool:
        return self._device_info["STOVETYPE"] in [2, 4, 6]

    @property
    def is_first_fan_on(self) -> bool:
        return bool(self._telemetry.get("F2LF", 0))

    @property
    def has_fan_mode_silent(self) -> bool:
        return int(self._device_info.get("FAN2TYPE", 0)) > 2

    @property
    def has_fan_mode_auto(self) -> bool:
        return self._device_info.get("FAN2MODE", 0) in [2, 3]

    @property
    def has_fan_mode_high(self) -> bool:
        return self._device_info.get("FAN2MODE", 0) == 3

    @property
    def has_fan_mode_prop(self) -> bool:
        return self._device_info.get("FAN2MODE", 0) == 4

    @property
    def has_main_fan(self) -> bool:
        return int(self._device_info.get("FAN2TYPE", 0)) > 1

    @property
    def has_left_fan(self) -> bool:
        return int(self._device_info.get("FAN2TYPE", 0)) > 3

    @property
    def has_right_fan(self) -> bool:
        return int(self._device_info.get("FAN2TYPE", 0)) > 2

    @property
    def has_leveltronic_pellet_sensor(self) -> bool:
        return self._device_info.get("PSENSTYPE", 0) == 1

    @property
    def has_capacitive_pellet_sensor(self) -> bool:
        return self._device_info.get("PSENSTYPE", 0) == 2

    @property
    def pellet_level_min(self) -> float:
        return float(self._device_info.get("PSENSLMIN", 0))

    @property
    def pellet_level_max(self) -> float:
        return float(self._device_info.get("PSENSLMAX", 0))

    @property
    def pellet_level_threshold(self) -> float:
        return float(self._device_info.get("PSENSLTSH", 0))

    @property
    def pellet_level(self) -> float:
        return float(self._telemetry.get("PLEVEL", 0))

    @property
    def has_wood_combustion_temperature(self) -> bool:
        return self._device_info["STOVETYPE"] in [7, 8]

    @property
    def has_air_outlet_temperature(self) -> bool:
        return (
            self._device_info["STOVETYPE"] in [7, 8]
            and int(self._device_info["FAN2TYPE"]) > 1
        )

    @property
    def has_door_control(self) -> bool:
        return self._device_info.get("DOORMOTOR", 0) == 1

    @property
    def has_light_control(self) -> bool:
        return self._device_info.get("LIGHTCONT", 0) == 1

    @property
    def product_type(self) -> int:
        return int(self._device_info.get("STOVETYPE", 0))

    @property
    def is_product_on(self) -> bool:
        return self._telemetry["STATUS"] not in [0, 1]

    @property
    def hydro_t1_temperature(self) -> float:
        return float(self._telemetry.get("T1", 0))

    @property
    def hydro_t2_temperature(self) -> float:
        return float(self._telemetry.get("T2", 0))

    @property
    def wood_combustion_temperature(self) -> float:
        return float(self._telemetry.get("T3", 0))

    @property
    def air_outlet_temperature(self) -> float:
        return float(self._telemetry.get("T4", 0))

    def _main_temperature_probe_index(self) -> int:
        if self.is_hydro:
            if self._device_info["UICONFIG"] == 1:
                return 1  # T2
            if self._device_info["UICONFIG"] == 10:
                return 4  # T5
        return int(self._device_info["MAINTPROBE"])

    def _main_temperature_description(self) -> TemperatureDescriptionKey:
        if self.is_hydro:
            if self._device_info["UICONFIG"] == 1:
                return TemperatureDescriptionKey.RETURN_WATER_TEMP
            if self._device_info["UICONFIG"] in [3, 4]:
                return TemperatureDescriptionKey.TANK_WATER_TEMP
        return TemperatureDescriptionKey.ROOM_TEMP

    @property
    def current_temperature(self) -> float:
        return float(
            self._telemetry[TEMPERATURE_PROBES[self._main_temperature_probe_index()]]
        )

    @property
    def T1(self) -> float:
        return float(self._telemetry.get("T1", 0))

    @property
    def T2(self) -> float:
        return float(self._telemetry.get("T2", 0))

    @property
    def T3(self) -> float:
        return float(self._telemetry.get("T3", 0))

    @property
    def T4(self) -> float:
        return float(self._telemetry.get("T4", 0))

    @property
    def T5(self) -> float:
        return float(self._telemetry.get("T5", 0))

    @property
    def power_mode(self) -> int:
        return int(self._telemetry.get("PWR", 0))

    @property
    def target_temperature_min(self) -> int:
        return int(self._device_info.get("SPLMIN", 0))

    @property
    def target_temperature_max(self) -> int:
        return int(self._device_info.get("SPLMAX", 0))

    @property
    def target_temperature(self) -> int:
        return int(self._telemetry.get("SETP", 0))

    @property
    def main_fan_speed(self) -> int:
        return int(self._telemetry.get("F2L", 0))

    @property
    def left_fan_speed(self) -> int:
        return int(self._telemetry.get("F3L", 0))

    @property
    def right_fan_speed(self) -> int:
        return int(self._telemetry.get("F4L", 0))

    @property
    def main_fan_min(self) -> int:
        return int(self._telemetry["FANLMINMAX"][0])

    @property
    def main_fan_max(self) -> int:
        return int(self._telemetry["FANLMINMAX"][1])

    @property
    def left_fan_min(self) -> int:
        return int(self._telemetry["FANLMINMAX"][2])

    @property
    def left_fan_max(self) -> int:
        return int(self._telemetry["FANLMINMAX"][3])

    @property
    def right_fan_min(self) -> int:
        return int(self._telemetry["FANLMINMAX"][4])

    @property
    def right_fan_max(self) -> int:
        return int(self._telemetry["FANLMINMAX"][5])

    @property
    def door_status(self) -> int:
        return int(self._telemetry.get("DOOR", 0))

    @property
    def light_status(self) -> int:
        return int(self._telemetry.get("LGHT", self._telemetry.get("LIGHT", 0)))

    @property
    def status(self) -> int:
        return int(self._telemetry.get("LSTATUS", 0))

    @property
    def mac(self) -> str:
        return str(self._device_info.get("MAC", "X"))

    @property
    def name(self) -> str:
        return str(self._device_info.get("LABEL", "X"))

    @property
    def pellet_quantity(self) -> int:
        return int(self._telemetry.get("PQT", 0))

    @property
    def is_on(self) -> bool:
        return self._telemetry["LSTATUS"] not in OFF_STATUSES

    @property
    def is_heating(self) -> bool:
        return bool(self._telemetry["LSTATUS"] in HEATING_STATUSES)

    @property
    def sw_version(self) -> str:
        return str(self._device_info.get("plzbridge", "X"))

    @property
    def hw_version(self) -> str:
        return str(self._device_info.get("SYSTEM", "X"))

    def list_temperatures(self) -> list[TemperatureDefinition]:
        """Return a list of temperature sensor definitions"""
        result: list[TemperatureDefinition] = []

        result.append(
            TemperatureDefinition(
                state_property=TEMPERATURE_PROBES[self._main_temperature_probe_index()],
                description_key=self._main_temperature_description(),
            ),
        )

        if self.has_air_outlet_temperature or self.air_outlet_temperature != 0:
            result.append(
                TemperatureDefinition(
                    state_property="T4",
                    description_key=TemperatureDescriptionKey.AIR_OUTLET_TEMP,
                ),
            )

        if (
            self.has_wood_combustion_temperature
            or self.wood_combustion_temperature != 0
        ):
            result.append(
                TemperatureDefinition(
                    state_property="T3",
                    description_key=TemperatureDescriptionKey.WOOD_COMBUSTION_TEMP,
                ),
            )

        if self.is_hydro:
            result.append(
                TemperatureDefinition(
                    state_property="T1",
                    description_key=TemperatureDescriptionKey.T1_HYDRO_TEMP,
                ),
            )
            result.append(
                TemperatureDefinition(
                    state_property="T2",
                    description_key=TemperatureDescriptionKey.T2_HYDRO_TEMP,
                ),
            )

        return result

    def to_dict(
        self,
        *,
        legacy_format: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Return a snapshot of the state."""
        if legacy_format:
            return {
                "properties": self._device_info.copy(),
                "attributes": self._telemetry.copy(),
            }
        return {
            "device_info": self._device_info.copy(),
            "telemetry": self._telemetry.copy(),
        }
