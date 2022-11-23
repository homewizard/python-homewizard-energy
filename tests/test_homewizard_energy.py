"""Test for HomeWizard Energy."""
from unittest.mock import patch

import aiohttp
import pytest

from homewizard_energy import HomeWizardEnergy
from homewizard_energy.errors import DisabledError, RequestError, UnsupportedError
from homewizard_energy.features import Features

from . import load_fixtures


@pytest.mark.asyncio
async def test_request_returns_json(aresponses):
    """Test JSON response is handled correctly."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)
        return_value = await api.request("api")
        assert isinstance(return_value, dict)
        assert return_value["status"] == "ok"
        await api.close()


@pytest.mark.asyncio
async def test_request_internal_session(aresponses):
    """Test session is closed when created internally."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )

    api = HomeWizardEnergy("example.com")
    assert await api.request("api")
    await api.close()


@pytest.mark.asyncio
async def test_request_returns_txt(aresponses):
    """Test request returns raw text when non-json."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/not-json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)
        return_value = await api.request("api")
        assert isinstance(return_value, str)
        assert return_value == '{"status": "ok"}'
        await api.close()


@pytest.mark.asyncio
async def test_request_detects_403(aresponses):
    """Test request detects disabled API."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=403,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with pytest.raises(DisabledError):
            await api.request("api")

        await api.close()


@pytest.mark.asyncio
async def test_request_detects_non_200(aresponses):
    """Test detects non-ok response."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=500,
            headers={"Content-Type": "application/json"},
            text='{"status": "ok"}',
        ),
    )
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with pytest.raises(RequestError):
            await api.request("api")

        await api.close()


@pytest.mark.asyncio
async def test_request_detects_clienterror():
    """Test other clienterror."""
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with patch.object(
            session, "request", side_effect=aiohttp.ClientError
        ), pytest.raises(RequestError):
            await api.request("api")

        await api.close()


@pytest.mark.asyncio
async def test_get_device_object(aresponses):
    """Test device object is fetched and sets detected values."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)
        device = await api.device()

        assert device
        assert device.product_type == "HWE-P1"

        # pylint: disable=protected-access
        assert api._features is not None

        await api.close()


@pytest.mark.asyncio
async def test_get_device_object_detects_invalid_api(aresponses):
    """Test raises error when invalid API is used."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device_invalid_api.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with pytest.raises(UnsupportedError):
            await api.device()

        await api.close()


@pytest.mark.asyncio
async def test_get_data_object(aresponses):
    """Test fetches data object and device object when unknown."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/data",
        "GET",
        aresponses.Response(
            text=load_fixtures("data_p1.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        data = await api.data()

        assert data
        assert data.smr_version == 50

        await api.close()


@pytest.mark.asyncio
async def test_get_data_object_with_known_device(aresponses):
    """Test fetches data object."""

    aresponses.add(
        "example.com",
        "/api/v1/data",
        "GET",
        aresponses.Response(
            text=load_fixtures("data_p1.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._detected_api_version = "v1"
        data = await api.data()

        assert data
        assert data.smr_version == 50

        await api.close()


@pytest.mark.asyncio
async def test_get_state_object(aresponses):
    """Test fetches state object and device object when unknown."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device_energysocket.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "GET",
        aresponses.Response(
            text=load_fixtures("state.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "1.00")

        state = await api.state()
        assert state
        assert not state.power_on

        await api.close()


@pytest.mark.asyncio
async def test_get_state_object_with_known_device(aresponses):
    """Test fetches state object."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device_energysocket.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "GET",
        aresponses.Response(
            text=load_fixtures("state.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "1.00")

        state = await api.state()
        assert state
        assert not state.power_on

        await api.close()


@pytest.mark.asyncio
async def test_get_state_object_returns_null_not_supported(aresponses):
    """Test detects device has no support for state."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/data",
        "GET",
        aresponses.Response(
            text=load_fixtures("state.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-P1", "1.00")

        state = await api.state()
        assert not state

        await api.close()


@pytest.mark.asyncio
async def test_state_set(aresponses):
    """Test state set."""

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "PUT",
        aresponses.Response(
            text=load_fixtures("state.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "1.00")

        state = await api.state_set(power_on=False, switch_lock=False, brightness=255)
        assert state

        await api.close()


@pytest.mark.asyncio
async def test_state_set_detects_no_statechange(aresponses):
    """Test state set does not send request when nothing is changed."""

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "PUT",
        aresponses.Response(
            text=load_fixtures("state.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "1.00")

        state = await api.state_set()
        assert not state


@pytest.mark.asyncio
async def test_identify(aresponses):
    """Test identify call."""

    aresponses.add(
        "example.com",
        "/api/v1/identify",
        "PUT",
        aresponses.Response(
            text=load_fixtures("identify.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "3.02")

        state = await api.identify()
        assert state

        await api.close()


@pytest.mark.asyncio
async def test_identify_not_available(aresponses):
    """Test identify call when not supported."""

    aresponses.add(
        "example.com",
        "/api/v1/identify",
        "PUT",
        aresponses.Response(
            text=load_fixtures("identify.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "1.00")

        with pytest.raises(UnsupportedError):
            await api.identify()

        await api.close()


@pytest.mark.asyncio
async def test_get_system_object(aresponses):
    """Test fetches system object and device object when unknown."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("device_energysocket.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=load_fixtures("system_cloud_enabled.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=load_fixtures("system_cloud_disabled.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "1.00")

        system = await api.system()
        assert system
        assert system.cloud_enabled

        system = await api.system()
        assert system
        assert not system.cloud_enabled

        await api.close()


@pytest.mark.asyncio
async def test_system_set(aresponses):
    """Test system set."""

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "PUT",
        aresponses.Response(
            text=load_fixtures("system_cloud_disabled.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # pylint: disable=protected-access
        api._features = Features("HWE-SKT", "3.01")

        system = await api.system_set(enable_cloud=False)
        assert system

        await api.close()
