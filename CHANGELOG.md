# Changelog

## 0.1.18
* Bugfix: missing current_fan_speed function

## 0.1.17
* Second and third fans control
* Code quality improvements

## 0.1.16
* Fix the silent mode
* Make fan speed 0 available
* Fix a bug that throws an exception when listing the temperatiures on hydro stoves (issue #6)

## 0.1.15
* Add more devices for test mocks
* Sanitize the pellets quantity to prevent the value from decreasing
* Bugfix: distinguish fan speed 0 from silent
* Bugfix: redact the wifi address when a redacted json is requested

## 0.1.14
* Make status codes lower case
* Add `to_dict` function, allow to redact sensitive info
* Allows an `aiohttp.ClientSession` to be passed in the `PalazzettiClient` constructor

## 0.1.13
* Refactor temperatures and undeprecate `T1`, `T2`, `T3`, `T4`, `T5`
* Expose `has_pellet_level` and `pellet_level`

## 0.1.12
* Fix `is_heating` state: remove ECOMODE (51) is not considered heating anymore
* Refactor the temperature sensors. `PalazzettiClient.list_temperatures` will return a list of labelled temperature sensors that are present
* `T1`, `T2`, `T3`, `T4`, `T5` properties of `PalazzettiClient` are marked as deprecated

## 0.1.11
* Fix temperature sensors

## 0.1.10
* Fix `setup.py`

## 0.1.9
* Fix `setup.py` (thanks @joostlek, @onkelbeh).
* Add `CHANGELOG.md`

## 0.1.8
* Return the user-provided `host` value instead of an internal property.

## 0.1.7
* Add the `is_on` property, which is different from `is_heating`.

## 0.1.6
* First version usable in Home Assistant with all the important state values.