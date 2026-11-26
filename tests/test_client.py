"""Test the PalazzettiClient class."""

import asyncio
from unittest.mock import patch

import aiohttp
import pytest

from pypalazzetti.client import PalazzettiClient
from pypalazzetti.config import PalazzettiClientConfig
from pypalazzetti.exceptions import CommunicationError, ValidationError
from pypalazzetti.state import _PalazzettiAPIData
from pypalazzetti.temperature import TemperatureDescriptionKey


def stdt_response(device: str = "palazzetti_ginger"):
    with open(f"./tests/mock_json/{device}/GET_STDT.json") as f:
        return f.read()


def alls_response(device: str = "palazzetti_ginger", variant: str | None = None):
    variant_modifier = ("_" + variant) if variant else ""
    with open(f"./tests/mock_json/{device}/GET_ALLS{variant_modifier}.json") as f:
        return f.read()


class MockResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


@pytest.fixture
def mock_stdt_response_ok(device: str = "palazzetti_ginger"):
    return MockResponse(status=200, text=stdt_response(device=device))


@pytest.fixture
def mock_alls_response_ok(device: str = "palazzetti_ginger"):
    return MockResponse(status=200, text=alls_response(device=device))


@pytest.fixture
def mock_alls_smaller_pqt(
    device: str = "palazzetti_ginger", variant: str | None = None
):
    return MockResponse(
        status=200, text=alls_response(device=device, variant="smaller_PQT")
    )


@pytest.fixture
def mock_alls_larger_pqt(device: str = "palazzetti_ginger", variant: str | None = None):
    return MockResponse(
        status=200, text=alls_response(device=device, variant="larger_PQT")
    )


async def mock_ready_client(
    device: str = "palazzetti_ginger", variant: str | None = None
):
    client = PalazzettiClient("127.0.0.1")

    # Connect and set properties
    with (
        patch(
            "aiohttp.ClientSession.get",
            return_value=MockResponse(status=200, text=stdt_response(device=device)),
        ),
    ):
        assert await client.connect()

    # Set state attributes
    with (
        patch(
            "aiohttp.ClientSession.get",
            return_value=MockResponse(status=200, text=alls_response(device=device)),
        ),
    ):
        assert await client.update_state()

    return client


async def test_connect():
    """Test the connect function."""
    client = PalazzettiClient("127.0.0.1")
    with patch(
        "pypalazzetti.client.PalazzettiClient._execute_command",
        return_value=_PalazzettiAPIData(stdt_response()),
    ) as exec:
        success = await client.connect()

    assert len(exec.mock_calls) == 1
    assert success


async def test_execute_command(mock_stdt_response_ok):
    """Test the _execute_command function"""
    client = PalazzettiClient("127.0.0.1")

    with (
        patch("aiohttp.ClientSession.get", return_value=mock_stdt_response_ok) as get,
    ):
        success = await client._execute_command(command="GET STDT")

    assert len(get.mock_calls) == 1
    assert success


async def test_state_ginger(mock_stdt_response_ok, mock_alls_response_ok):
    """Test the functions that return the state."""
    client = PalazzettiClient("127.0.0.1")

    # Connect and set properties
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_stdt_response_ok),
    ):
        assert await client.connect()

    # Set state attributes
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_response_ok),
    ):
        assert await client.update_state()

    assert client.is_on
    assert not client.is_heating
    assert client.target_temperature == 21
    assert client.host == "127.0.0.1"
    assert client.mac == "40:F3:85:71:23:45"
    assert client.pellet_quantity == 1807
    assert client.power_mode == 3
    assert client.fan_speed == 6
    assert client.status == 51
    assert client.name == "Name"
    temperatures = {
        sensor.description_key: getattr(client, sensor.state_property)
        for sensor in client.list_temperatures()
    }
    assert len(temperatures) == 2
    assert temperatures[TemperatureDescriptionKey.ROOM_TEMP] == 21.5
    assert temperatures[TemperatureDescriptionKey.WOOD_COMBUSTION_TEMP] == 45


async def test_set_fan_speed(mock_stdt_response_ok, mock_alls_response_ok):
    """Test the functions that return the state."""
    client = PalazzettiClient("127.0.0.1")

    # Connect and set properties
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_stdt_response_ok),
    ):
        assert await client.connect()

    # Set state attributes
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_response_ok) as get,
    ):
        assert await client.update_state()
        assert await client.set_fan_speed(0)

    assert get.mock_calls[-1].args[0].split("=")[-1] == "SET RFAN 0"


async def test_pellet_quantity_not_sanitize(
    mock_alls_response_ok,
    mock_alls_smaller_pqt,
    mock_alls_larger_pqt,
):
    client = PalazzettiClient(
        "127.0.0.1", config=PalazzettiClientConfig(pellet_quantity_sanitize=False)
    )

    # Set state attributes
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_response_ok),
    ):
        assert await client.update_state()

    assert client.pellet_quantity == 1807

    # Set a smaller PQT
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_smaller_pqt),
    ):
        assert await client.update_state()
    assert client.pellet_quantity == 1500

    # Set a smaller PQT
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_larger_pqt),
    ):
        assert await client.update_state()
    assert client.pellet_quantity == 2000


async def test_pellet_quantity_sanitize(
    mock_alls_response_ok,
    mock_alls_smaller_pqt,
    mock_alls_larger_pqt,
):
    client = PalazzettiClient(
        "127.0.0.1", config=PalazzettiClientConfig(pellet_quantity_sanitize=True)
    )

    # Set state attributes
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_response_ok),
    ):
        assert await client.update_state()

    assert client.pellet_quantity == 1807

    # Set a smaller PQT
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_smaller_pqt),
    ):
        assert await client.update_state()
    assert client.pellet_quantity == 1807

    # Set a smaller PQT
    with (
        patch("aiohttp.ClientSession.get", return_value=mock_alls_larger_pqt),
    ):
        assert await client.update_state()
    assert client.pellet_quantity == 2000


@pytest.mark.parametrize(
    "device",
    [
        "jotul_pf911s",
        "palazzetti_aurora",
        "palazzetti_beatrice",
        "palazzetti_emily",
        "palazzetti_ginger",
        "palazzetti_juliepro2",
    ],
)
async def test_snapshot(device, snapshot):
    """Perform snapshot tests"""
    client = await mock_ready_client(device=device)

    assert client == snapshot
    assert client._state == snapshot


async def test_timeout_raises_communication_error():
    """Test that a request timeout raises CommunicationError and resets connected."""
    client = PalazzettiClient("127.0.0.1")

    with (
        patch("aiohttp.ClientSession.get", side_effect=TimeoutError("Request timeout")),
        pytest.raises(CommunicationError, match=r"API request timed out after 25\.0s"),
    ):
        await client.connect()

    assert not client.connected

    with (
        patch("aiohttp.ClientSession.get", side_effect=TimeoutError("Async timeout")),
        pytest.raises(CommunicationError, match=r"API request timed out after 25\.0s"),
    ):
        await client.update_state()

    assert not client.connected


async def test_update_state_does_not_refetch_properties_on_reconnect(
    mock_stdt_response_ok,
    mock_alls_response_ok,
):
    """Test that transient poll failure does not trigger GET STDT on next poll."""
    client = PalazzettiClient("127.0.0.1")

    # Initial connect
    with patch(
        "aiohttp.ClientSession.get", return_value=mock_stdt_response_ok
    ) as mock_get:
        assert await client.connect()
        assert len(mock_get.mock_calls) == 1
        assert "GET STDT" in mock_get.mock_calls[0].args[0]

    # First update_state
    with patch(
        "aiohttp.ClientSession.get", return_value=mock_alls_response_ok
    ) as mock_get:
        assert await client.update_state()
        assert len(mock_get.mock_calls) == 1
        assert "GET ALLS" in mock_get.mock_calls[0].args[0]
        assert client.connected

    # Transient network error on poll
    with patch(
        "aiohttp.ClientSession.get",
        side_effect=aiohttp.ClientConnectionError("Connection lost"),
    ):
        with pytest.raises(CommunicationError):
            await client.update_state()
        assert not client.connected

    # Reconnect poll: must ONLY send GET ALLS, never GET STDT
    with patch(
        "aiohttp.ClientSession.get", return_value=mock_alls_response_ok
    ) as mock_get:
        assert await client.update_state()
        assert len(mock_get.mock_calls) == 1
        assert "GET ALLS" in mock_get.mock_calls[0].args[0]
        assert "GET STDT" not in mock_get.mock_calls[0].args[0]
        assert client.connected


async def test_command_serialization_lock():
    """Test that API commands are serialized through the internal lock."""
    client = PalazzettiClient("127.0.0.1")
    execution_order: list[str] = []

    def mock_get(url, *args, **kwargs):
        name = "cmd1" if "GET STDT" in url else "cmd2"
        delay = 0.05 if name == "cmd1" else 0.01

        class DelayedResponse(MockResponse):
            async def text(self):
                await asyncio.sleep(delay)
                execution_order.append(name)
                return stdt_response()

        return DelayedResponse(status=200, text=stdt_response())

    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        t1 = asyncio.create_task(client._execute_command("GET STDT", merge_state=False))
        await asyncio.sleep(0.005)
        t2 = asyncio.create_task(client._execute_command("GET ALLS", merge_state=False))
        await asyncio.gather(t1, t2)

    assert execution_order == ["cmd1", "cmd2"]


def test_default_request_timeout():
    """Test default request timeout value in config."""
    config = PalazzettiClientConfig()
    assert config.request_timeout == 25.0


async def test_custom_request_timeout(mock_stdt_response_ok):
    """Test that custom request timeout from config is applied to session.get."""
    config = PalazzettiClientConfig(request_timeout=4.5)
    client = PalazzettiClient("127.0.0.1", config=config)

    with patch(
        "aiohttp.ClientSession.get", return_value=mock_stdt_response_ok
    ) as mock_get:
        await client._execute_command("GET STDT")
        assert len(mock_get.mock_calls) == 1
        timeout_arg = mock_get.mock_calls[0].kwargs.get("timeout")
        assert timeout_arg is not None
        assert timeout_arg.total == 4.5


async def test_light_control():
    """Test light control commands and state properties."""
    client = PalazzettiClient("127.0.0.1")
    stdt_with_light = stdt_response().replace(
        '"HWTYPE": 6,', '"HWTYPE": 6,\n    "LIGHTCONT": 1,'
    )
    alls_with_light = alls_response().replace(
        '"LSTATUS": 51,', '"LSTATUS": 51,\n    "LGHT": 1,'
    )

    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(status=200, text=stdt_with_light),
    ):
        assert await client.connect()

    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(status=200, text=alls_with_light),
    ):
        assert await client.update_state()

    assert client.has_light_control is True
    assert client.light_status == 1
    assert client.is_light_on is True

    # Turn light off
    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(
            status=200, text='{"SUCCESS": true, "DATA": {"LGHT": 0}}'
        ),
    ) as get:
        assert await client.set_light(False)
        assert get.mock_calls[-1].args[0].split("=")[-1] == "SET LGHT 0"
        assert client.is_light_on is False
        assert client.light_status == 0

    # Turn light on
    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(
            status=200, text='{"SUCCESS": true, "DATA": {"LGHT": 1}}'
        ),
    ) as get:
        assert await client.set_light(True)
        assert get.mock_calls[-1].args[0].split("=")[-1] == "SET LGHT 1"
        assert client.is_light_on is True
        assert client.light_status == 1


async def test_light_control_not_available():
    """Test that set_light raises ValidationError when not supported."""
    client = await mock_ready_client()
    assert client.has_light_control is False

    with pytest.raises(ValidationError, match="Light control not available."):
        await client.set_light(True)


async def test_door_control():
    """Test motorized door control commands and state properties."""
    client = PalazzettiClient("127.0.0.1")
    stdt_with_door = stdt_response().replace(
        '"HWTYPE": 6,', '"HWTYPE": 6,\n    "DOORMOTOR": 1,'
    )
    alls_with_door = alls_response().replace(
        '"LSTATUS": 51,', '"LSTATUS": 51,\n    "DOOR": 0,'
    )

    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(status=200, text=stdt_with_door),
    ):
        assert await client.connect()

    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(status=200, text=alls_with_door),
    ):
        assert await client.update_state()

    assert client.has_door_control is True
    assert client.door_status == 0
    assert client.is_door_open is False

    # Open door -> SET DOOR 1
    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(
            status=200, text='{"SUCCESS": true, "DATA": {"DOOR": 1}}'
        ),
    ) as get:
        assert await client.set_door(True)
        assert get.mock_calls[-1].args[0].split("=")[-1] == "SET DOOR 1"
        assert client.is_door_open is True
        assert client.door_status == 1

    # Close door -> SET DOOR 2
    with patch(
        "aiohttp.ClientSession.get",
        return_value=MockResponse(
            status=200, text='{"SUCCESS": true, "DATA": {"DOOR": 0}}'
        ),
    ) as get:
        assert await client.set_door(False)
        assert get.mock_calls[-1].args[0].split("=")[-1] == "SET DOOR 2"
        assert client.is_door_open is False
        assert client.door_status == 0

    # Non-zero door status (e.g. moving/open code 2) indicates open
    client._state.merge_telemetry(
        _PalazzettiAPIData('{"SUCCESS": true, "DATA": {"DOOR": 2}}')
    )
    assert client.door_status == 2
    assert client.is_door_open is True


async def test_door_control_not_available():
    """Test that set_door raises ValidationError when not supported."""
    client = await mock_ready_client()
    assert client.has_door_control is False

    with pytest.raises(ValidationError, match="Door control not available."):
        await client.set_door(True)


async def test_light_status_parsing():
    """Test parsing light status with both LGHT and LIGHT keys."""
    client = PalazzettiClient("127.0.0.1")

    # With LGHT key
    client._state.merge_telemetry(
        _PalazzettiAPIData('{"SUCCESS": true, "DATA": {"LGHT": 1}}')
    )
    assert client.light_status == 1
    assert client.is_light_on is True

    # With LIGHT fallback key (normalized to LGHT)
    client._state._telemetry.clear()
    client._state.merge_telemetry(
        _PalazzettiAPIData('{"SUCCESS": true, "DATA": {"LIGHT": 1}}')
    )
    assert client.light_status == 1
    assert client.is_light_on is True

    # Updating LIGHT to 0 properly reflects in light_status without stale shadowing
    client._state.merge_telemetry(
        _PalazzettiAPIData('{"SUCCESS": true, "DATA": {"LIGHT": 0}}')
    )
    assert client.light_status == 0
    assert client.is_light_on is False

    # With neither
    client._state._telemetry.clear()
    assert client.light_status == 0
    assert client.is_light_on is False


async def test_to_dict_and_to_json_formats():
    """Test to_dict and to_json with default modern and backward-compatible legacy formats."""
    import warnings

    client = await mock_ready_client()

    # Modern format (default in 0.2.0) emits ZERO warnings
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        data_default = client.to_dict()
        json_default = client.to_json()
    assert len(recorded) == 0

    assert "device_info" in data_default["state"]
    assert "telemetry" in data_default["state"]
    assert "properties" not in data_default["state"]
    assert "attributes" not in data_default["state"]

    assert '"device_info":' in json_default
    assert '"telemetry":' in json_default
    assert '"properties":' not in json_default
    assert '"attributes":' not in json_default

    # Backward-compatible legacy format with legacy=True emits exactly 1 warning pointing to caller
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        data_legacy_kw = client.to_dict(legacy=True)
    assert len(recorded) == 1
    assert issubclass(recorded[0].category, DeprecationWarning)
    assert recorded[0].filename == __file__

    assert "properties" in data_legacy_kw["state"]
    assert "attributes" in data_legacy_kw["state"]
    assert "device_info" not in data_legacy_kw["state"]
    assert "telemetry" not in data_legacy_kw["state"]

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        json_legacy_kw = client.to_json(legacy=True)
    assert len(recorded) == 1
    assert issubclass(recorded[0].category, DeprecationWarning)
    assert recorded[0].filename == __file__

    assert '"properties":' in json_legacy_kw
    assert '"attributes":' in json_legacy_kw

    # Backward-compatible legacy format with legacy_format=True emits exactly 1 warning
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        data_legacy = client.to_dict(legacy_format=True)
    assert len(recorded) == 1
    assert issubclass(recorded[0].category, DeprecationWarning)
    assert recorded[0].filename == __file__

    assert "properties" in data_legacy["state"]
    assert "attributes" in data_legacy["state"]

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        json_legacy = client.to_json(legacy_format=True)
    assert len(recorded) == 1
    assert issubclass(recorded[0].category, DeprecationWarning)
    assert recorded[0].filename == __file__

    assert '"properties":' in json_legacy
    assert '"attributes":' in json_legacy

    # Explicit legacy_format=False / legacy=False emit ZERO warnings
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        data_modern_explicit = client.to_dict(legacy_format=False)
        data_legacy_false = client.to_dict(legacy=False)
        json_modern_explicit = client.to_json(legacy_format=False)
        json_legacy_false = client.to_json(legacy=False)
    assert len(recorded) == 0

    assert "device_info" in data_modern_explicit["state"]
    assert "telemetry" in data_modern_explicit["state"]
    assert "device_info" in data_legacy_false["state"]
    assert "telemetry" in data_legacy_false["state"]
    assert '"device_info":' in json_modern_explicit
    assert '"device_info":' in json_legacy_false

    # Conflicting arguments raise ValueError
    with pytest.raises(ValueError, match="Conflicting arguments"):
        client.to_dict(legacy=True, legacy_format=False)
    with pytest.raises(ValueError, match="Conflicting arguments"):
        client.to_dict(legacy=False, legacy_format=True)
    with pytest.raises(ValueError, match="Conflicting arguments"):
        client.to_json(legacy=True, legacy_format=False)
    with pytest.raises(ValueError, match="Conflicting arguments"):
        client.to_json(legacy=False, legacy_format=True)
    with pytest.raises(ValueError, match="Conflicting arguments"):
        client._state.to_dict(legacy=True, legacy_format=False)

    # Direct _PalazzettiState.to_dict calls
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        state_default = client._state.to_dict()
    assert len(recorded) == 0
    assert "device_info" in state_default
    assert "telemetry" in state_default

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        state_legacy = client._state.to_dict(legacy=True)
    assert len(recorded) == 1
    assert issubclass(recorded[0].category, DeprecationWarning)
    assert recorded[0].filename == __file__
    assert "properties" in state_legacy
    assert "attributes" in state_legacy

    # Redaction with modern and legacy formats
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        redacted_legacy = client.to_dict(redact=True, legacy=True)
    assert redacted_legacy["host"] == "XXXXXXXX"
    assert redacted_legacy["state"]["properties"]["MAC"] == "XXXXXXXX"
    assert redacted_legacy["state"]["attributes"]["MAC"] == "XXXXXXXX"

    redacted_modern = client.to_dict(redact=True)
    assert redacted_modern["host"] == "XXXXXXXX"
    assert redacted_modern["state"]["device_info"]["MAC"] == "XXXXXXXX"
    assert redacted_modern["state"]["telemetry"]["MAC"] == "XXXXXXXX"

    json_redacted = client.to_json(redact=True)
    assert '"host": "XXXXXXXX"' in json_redacted
    assert '"MAC": "XXXXXXXX"' in json_redacted


async def test_backward_compatibility_deprecated_api():
    """Test deprecated methods, properties, and constants."""
    from pypalazzetti.const import (
        COMMAND_GET_DEVICE_INFO,
        COMMAND_GET_TELEMETRY,
        COMMAND_UPDATE_PROPERTIES,
        COMMAND_UPDATE_STATE,
    )

    client = PalazzettiClient("127.0.0.1")

    # Test _has_properties getter and setter
    assert client._has_properties is False
    client._has_properties = True
    assert client._has_device_info is True
    assert client._has_properties is True

    # Test merge_properties deprecation warning
    with pytest.deprecated_call():
        client._state.merge_properties(
            _PalazzettiAPIData('{"SUCCESS": true, "DATA": {"TEST_PROP": 1}}')
        )
    assert client._state._device_info.get("TEST_PROP") == 1
    assert client._state._properties.get("TEST_PROP") == 1

    # Test merge_state deprecation warning
    with pytest.deprecated_call():
        client._state.merge_state(
            _PalazzettiAPIData('{"SUCCESS": true, "DATA": {"TEST_ATTR": 2}}')
        )
    assert client._state._telemetry.get("TEST_ATTR") == 2
    assert client._state._attributes.get("TEST_ATTR") == 2

    # Test constants aliases
    assert COMMAND_UPDATE_PROPERTIES == COMMAND_GET_DEVICE_INFO
    assert COMMAND_UPDATE_STATE == COMMAND_GET_TELEMETRY


async def test_update_telemetry(mock_stdt_response_ok, mock_alls_response_ok):
    """Test update_telemetry alias."""
    client = PalazzettiClient("127.0.0.1")
    with patch("aiohttp.ClientSession.get", return_value=mock_stdt_response_ok):
        assert await client.connect()
    with patch("aiohttp.ClientSession.get", return_value=mock_alls_response_ok):
        assert await client.update_telemetry()
    assert client.connected
