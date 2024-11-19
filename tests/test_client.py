"""Test the PalazzettiClient class."""

from pypalazzetti.client import PalazzettiClient
from pypalazzetti.state import _PalazzettiAPIData
from pypalazzetti.temperature import TemperatureDescriptionKey
from unittest.mock import patch
import pytest


def stdt_response(device: str = "palazzetti_ginger"):
    with open(f"./tests/mock_json/{device}/GET_STDT.json", "r") as f:
        return f.read()


def alls_response(device: str = "palazzetti_ginger"):
    with open(f"./tests/mock_json/{device}/GET_ALLS.json", "r") as f:
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
def mock_stdt_response_ok():
    return MockResponse(status=200, text=stdt_response())


@pytest.fixture
def mock_alls_response_ok():
    return MockResponse(status=200, text=alls_response())


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

    # assert len(session.mock_calls) == 1
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

    # Connect and set state attributes
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
