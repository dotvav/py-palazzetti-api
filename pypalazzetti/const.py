"""Constants."""

from typing import Final

API_COMMAND_URL_TEMPLATE: Final = (
    "http://{host}/cgi-bin/sendmsg.lua?cmd={command_and_parameter}"
)

STATUSES: Final[dict[int, str]] = {
    0: "off",
    1: "off_timer",
    2: "test_fire",
    3: "heatup",
    4: "fueling",
    5: "ign_test",
    6: "burning",
    7: "burning_mod",
    8: "unknown",
    9: "cool_fluid",
    10: "fire_stop",
    11: "clean_fire",
    12: "cooling",
    50: "cleanup",
    51: "ecomode",
    241: "chimney_alarm",
    243: "grate_error",
    244: "pellet_water_error",
    245: "t05_error",
    247: "hatch_door_open",
    248: "pressure_error",
    249: "main_probe_failure",
    250: "flue_probe_failure",
    252: "exhaust_temp_high",
    253: "pellet_finished",
    501: "off",
    502: "fueling",
    503: "ign_test",
    504: "burning",
    505: "firewood_finished",
    506: "cooling",
    507: "clean_fire",
    1000: "general_error",
    1001: "general_error",
    1239: "door_open",
    1240: "temp_too_high",
    1241: "cleaning_warning",
    1243: "fuel_error",
    1244: "pellet_water_error",
    1245: "t05_error",
    1247: "hatch_door_open",
    1248: "pressure_error",
    1249: "main_probe_failure",
    1250: "flue_probe_failure",
    1252: "exhaust_temp_high",
    1253: "pellet_finished",
    1508: "general_error",
}

HEATING_STATUSES: Final = [2, 3, 4, 5, 6, 7, 502, 503, 504]
OFF_STATUSES: Final = [0, 1]
TEMPERATURE_PROBES: Final = ["T1", "T2", "T3", "T4", "T5"]

FAN_SILENT: Final = "SILENT"
FAN_HIGH: Final = "HIGH"
FAN_AUTO: Final = "AUTO"
FAN_MODES: Final = [FAN_SILENT, "1", "2", "3", "4", "5", FAN_HIGH, FAN_AUTO]

COMMAND_CHECK_ONLINE: Final = "GET STAT"
COMMAND_UPDATE_PROPERTIES: Final = "GET STDT"
COMMAND_UPDATE_STATE: Final = "GET ALLS"
COMMAND_SET_TEMPERATURE: Final = "SET SETP"
COMMAND_SET_FAN_SPEED: Final = "SET RFAN"
COMMAND_SET_FAN_SILENT: Final = "SET SLNT 1"
COMMAND_SET_POWER_MODE: Final = "SET POWR"
COMMAND_SET_ON: Final = "CMD ON"
COMMAND_SET_OFF: Final = "CMD OFF"

REDACTED_DATA: Final = "XXXXXXXX"
