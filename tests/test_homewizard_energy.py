"""Test for HomeWizard Energy."""
import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from homewizard_energy import HomeWizardEnergy
from homewizard_energy.errors import DisabledError, RequestError, UnsupportedError

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


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


async def test_request_detects_clienterror():
    """Test other clienterror."""
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with patch.object(
            session, "request", side_effect=aiohttp.ClientError
        ), pytest.raises(RequestError):
            await api.request("api")

        await api.close()


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

        await api.close()


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

        state = await api.state()
        assert state
        assert not state.power_on

        await api.close()


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

        state = await api.state()
        assert state
        assert not state.power_on

        await api.close()


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

        state = await api.state_set(power_on=False, switch_lock=False, brightness=255)
        assert state

        await api.close()


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

        state = await api.state_set()
        assert not state


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

        state = await api.identify()
        assert state

        await api.close()


async def test_identify_not_available(aresponses):
    """Test identify call when not supported."""

    aresponses.add(
        "example.com",
        "/api/v1/identify",
        "PUT",
        aresponses.Response(
            text=load_fixtures("identify.json"),
            status=404,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with pytest.raises(UnsupportedError):
            await api.identify()

        await api.close()


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

        system = await api.system()
        assert system
        assert system.cloud_enabled

        system = await api.system()
        assert system
        assert not system.cloud_enabled

        await api.close()


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

        system = await api.system_set(cloud_enabled=False)
        assert system

        await api.close()


async def test_system_set_missing_arguments(aresponses):
    """Test system set when no arguments are given."""

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
        assert await api.system_set() is False


async def test_get_decryption_object(aresponses):
    """Test fetches decryption object."""

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
        "/api/v1/decryption",
        "GET",
        aresponses.Response(
            text=load_fixtures("decryption.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        decryption = await api.decryption()
        assert decryption
        assert decryption.key_set
        assert decryption.aad_set

        await api.close()


async def test_decryption_set(aresponses):
    """Test decryption set."""

    aresponses.add(
        "example.com",
        "/api/v1/decryption",
        "PUT",
        aresponses.Response(
            text=load_fixtures("decryption.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        # Catches invalid length
        with pytest.raises(ValueError):
            await api.decryption_set(key="00")

        with pytest.raises(ValueError):
            await api.decryption_set(aad="00")

        # Catches invalid content
        with pytest.raises(ValueError):
            await api.decryption_set(key="FAILccddeeff00112233445566778899")

        with pytest.raises(ValueError):
            await api.decryption_set(aad="30FAILccddeeff00112233445566778899")

        response = await api.decryption_set(
            key="aabbccddeeff00112233445566778899",
            aad="30aabbccddeeff00112233445566778899",
        )
        assert response

        await api.close()


async def test_decryption_set_no_arguments():
    """Test decryption set without arguments."""

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)
        assert await api.decryption_set() is False


async def test_decryption_set_generates_hit():
    """Test decryption set when len(AAD)==32."""

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        with pytest.raises(ValueError) as ex:
            await api.decryption_set(aad="aabbccddeeff00112233445566778899")
            assert "Hint" in str(ex.value)


async def test_decryption_reset(aresponses):
    """Test decryption reset."""

    aresponses.add(
        "example.com",
        "/api/v1/decryption",
        "DELETE",
        aresponses.Response(
            text=load_fixtures("decryption.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergy("example.com", clientsession=session)

        response = await api.decryption_reset(aad=True, key=True)
        assert response

        await api.close()


# pylint: disable=protected-access
async def test_request_timeout():
    """Test request raises timeout when request takes too long."""

    api = HomeWizardEnergy("example.com")
    api._session = AsyncMock()
    api._session.request = AsyncMock(side_effect=asyncio.TimeoutError())

    with pytest.raises(RequestError):
        await api.request("api/v1/data")

    assert api._session.request.call_count == 1


async def test_close_when_out_of_scope():
    """Test close called when object goes out of scope."""
    api = HomeWizardEnergy("example.com")
    api.close = AsyncMock()

    async with api as hwe:
        assert hwe == api

    assert api.close.call_count == 1
