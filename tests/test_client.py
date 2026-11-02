"""Test the PalazzettiClient class."""

import asyncio
from unittest.mock import patch

import aiohttp
import pytest

from pypalazzetti.client import PalazzettiClient
from pypalazzetti.config import PalazzettiClientConfig
from pypalazzetti.exceptions import CommunicationError
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
        pytest.raises(CommunicationError, match="API request timed out"),
    ):
        await client.connect()

    assert not client.connected

    with (
        patch("aiohttp.ClientSession.get", side_effect=TimeoutError("Async timeout")),
        pytest.raises(CommunicationError, match="API request timed out"),
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
