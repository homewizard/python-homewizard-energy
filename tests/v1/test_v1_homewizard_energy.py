"""Test for HomeWizard Energy."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy import HomeWizardEnergyV1
from homewizard_energy.errors import DisabledError, RequestError, UnsupportedError

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


async def test_request_returns_str(aresponses):
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
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        # pylint: disable=protected-access
        _, return_value = await api._request("api")
        assert isinstance(return_value, str)

        return_value = json.loads(return_value)
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

    api = HomeWizardEnergyV1("example.com")

    # pylint: disable=protected-access
    assert await api._request("api")
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
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        with pytest.raises(DisabledError):
            # pylint: disable=protected-access
            await api._request("api")

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
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        with pytest.raises(RequestError):
            # pylint: disable=protected-access
            await api._request("api")

        await api.close()


async def test_request_detects_clienterror():
    """Test other clienterror."""
    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        with (
            patch.object(session, "request", side_effect=aiohttp.ClientError),
            pytest.raises(RequestError),
        ):
            # pylint: disable=protected-access
            await api._request("api")

        await api.close()


### CombinedModels tests ###


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
@pytest.mark.parametrize(
    ("model", "device", "data", "state", "system"),
    [
        ("HWE-KWH1", "device", "data", None, "system"),
        ("HWE-KWH3", "device", "data", None, "system"),
        ("HWE-P1", "device", "data_all_data", None, "system"),
        ("HWE-SKT", "device", "data", "state_all", "system"),
        ("HWE-WTR", "device", "data", None, "system"),
        ("SDM230-wifi", "device", "data", None, "system"),
        ("SDM630-wifi", "device", "data", None, "system"),
    ],
)
async def test_combined_models_with_valid_authentication(
    model: str,
    device: str,
    data: str,
    state: str | None,
    system: str,
    snapshot: SnapshotAssertion,
    aresponses,
):
    """Test combined models request is successful when valid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{device}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/data",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{data}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{state}.json") if state else "404 Not Found",
            status=200 if state else 404,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{system}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV1("example.com") as api:
        data = await api.combined()
        assert data is not None
        assert data == snapshot


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
@pytest.mark.parametrize(
    ("model", "device", "data", "state", "system"),
    [
        ("HWE-KWH1", "device", "data", None, "system"),
        ("HWE-KWH3", "device", "data", None, "system"),
        ("HWE-P1", "device", "data_all_data", None, "system"),
        ("HWE-SKT", "device", "data", "state_all", "system"),
        ("HWE-WTR", "device", "data", None, "system"),
        ("SDM230-wifi", "device", "data", None, "system"),
        ("SDM630-wifi", "device", "data", None, "system"),
    ],
)
async def test_combined_models_with_valid_authentication_caches_device(
    model: str,
    device: str,
    data: str,
    state: str | None,
    system: str,
    snapshot: SnapshotAssertion,
    aresponses,
):
    """Test combined models request is successful when valid authentication is provided."""

    # Request 1
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{device}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/data",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{data}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{state}.json") if state else "404 Not Found",
            status=200 if state else 404,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{system}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    # Request 2, should use cache of `/api`
    aresponses.add(
        "example.com",
        "/api/v1/data",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{data}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{state}.json") if state else "404 Not Found",
            status=200 if state else 404,
            headers={"Content-Type": "application/json"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/{system}.json"),
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV1("example.com") as api:
        data = await api.combined()
        assert data is not None
        assert data == snapshot

        data_2 = await api.combined()
        assert data_2 == data


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["device"]),
        ("HWE-SKT", ["device"]),
        ("HWE-WTR", ["device"]),
        ("HWE-KWH1", ["device"]),
        ("HWE-KWH3", ["device"]),
        ("SDM230-wifi", ["device"]),
        ("SDM630-wifi", ["device"]),
    ],
)
async def test_get_device_object(
    model: str, fixtures: str, snapshot: SnapshotAssertion, aresponses
):
    """Test device object is fetched and sets detected values."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        async with aiohttp.ClientSession() as session:
            api = HomeWizardEnergyV1("example.com", clientsession=session)
            device = await api.device()

            assert device
            assert device.product_type == model

            assert device == snapshot

            await api.close()


async def test_get_device_used_cached_device_object(aresponses):
    """Test device object is fetched and sets detected values."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("HWE-P1/device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)
        device = await api.device()

        assert device
        assert device.product_type == "HWE-P1"

        device_2 = await api.device()
        assert device_2 == device

        await api.close()


async def test_get_device_with_clear_cache_flag(aresponses):
    """Test device object is fetched and sets detected values."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("HWE-P1/device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures("HWE-SKT/device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)
        device = await api.device()

        assert device
        assert device.product_type == "HWE-P1"

        device_2 = await api.device(reset_cache=True)
        assert device_2 != device

        assert device_2.product_type == "HWE-SKT"

        await api.close()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            ["data_all_data", "data_minimal", "data_no_gas", "data_single_phase"],
        ),
        ("HWE-SKT", ["data"]),
        ("HWE-WTR", ["data"]),
        ("HWE-KWH1", ["data"]),
        ("HWE-KWH3", ["data"]),
        ("SDM230-wifi", ["data"]),
        ("SDM630-wifi", ["data"]),
    ],
)
async def test_get_data_object(
    model: str, fixtures: str, snapshot: SnapshotAssertion, aresponses
):
    """Test fetches data object and device object when unknown."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/device.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        aresponses.add(
            "example.com",
            "/api/v1/data",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        async with aiohttp.ClientSession() as session:
            api = HomeWizardEnergyV1("example.com", clientsession=session)

            measurement = await api.measurement()
            assert measurement is not None
            assert measurement == snapshot

            await api.close()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            ["data_all_data", "data_minimal", "data_no_gas", "data_single_phase"],
        ),
        ("HWE-SKT", ["data"]),
        ("HWE-WTR", ["data"]),
        ("HWE-KWH1", ["data"]),
        ("HWE-KWH3", ["data"]),
        ("SDM230-wifi", ["data"]),
        ("SDM630-wifi", ["data"]),
    ],
)
async def test_get_data_object_with_known_device(
    model: str, fixtures: str, snapshot: SnapshotAssertion, aresponses
):
    """Test fetches data object."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api/v1/data",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        async with aiohttp.ClientSession() as session:
            api = HomeWizardEnergyV1("example.com", clientsession=session)

            # pylint: disable=protected-access
            api._detected_api_version = "v1"

            measurement = await api.measurement()
            assert measurement is not None
            assert measurement == snapshot

            await api.close()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-SKT",
            ["state_all", "state_power_on", "state_switch_lock", "state_brightness"],
        ),
    ],
)
async def test_get_state_object(
    model: str, fixtures: str, snapshot: SnapshotAssertion, aresponses
):
    """Test fetches state object and device object when unknown."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/device.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        aresponses.add(
            "example.com",
            "/api/v1/state",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        async with aiohttp.ClientSession() as session:
            api = HomeWizardEnergyV1("example.com", clientsession=session)

            state = await api.state()
            assert state is not None
            assert state == snapshot

            await api.close()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-SKT", ["state_all"]),
    ],
)
async def test_state_set(
    model: str, fixtures: str, snapshot: SnapshotAssertion, aresponses
):
    """Test state set."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api/v1/state",
            "PUT",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            ),
        )

        async with aiohttp.ClientSession() as session:
            api = HomeWizardEnergyV1("example.com", clientsession=session)

            state = await api.state(power_on=False, switch_lock=False, brightness=255)
            assert state
            assert state == snapshot
            await api.close()


@pytest.mark.parametrize(
    "model",
    [
        "HWE-P1",
        "HWE-SKT",
        "HWE-WTR",
    ],
)
async def test_identify(model: str, snapshot: SnapshotAssertion, aresponses):
    """Test identify call."""

    aresponses.add(
        "example.com",
        "/api/v1/identify",
        "PUT",
        aresponses.Response(
            text=load_fixtures(f"{model}/identify.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        state = await api.identify()
        assert state
        assert state == snapshot

        await api.close()


@pytest.mark.parametrize(
    "model",
    [
        "HWE-KWH1",
        "HWE-KWH3",
        "SDM230-wifi",
        "SDM630-wifi",
    ],
)
async def test_identify_not_supported(model: str, aresponses):
    """Test identify call when not supported."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=load_fixtures(f"{model}/device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/identify",
        "PUT",
        aresponses.Response(
            text="404 Not Found",
            status=404,
            headers={"Content-Type": "application/txt; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

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
            text=load_fixtures("HWE-SKT/device.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=json.dumps({"cloud_enabled": True}),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "GET",
        aresponses.Response(
            text=json.dumps({"cloud_enabled": False}),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        system = await api.system()
        assert system
        assert system.cloud_enabled

        system = await api.system()
        assert system
        assert not system.cloud_enabled

        await api.close()


@pytest.mark.parametrize(
    "model",
    [
        "HWE-P1",
        "HWE-SKT",
        "HWE-WTR",
        "HWE-KWH1",
        "HWE-KWH3",
        "SDM230-wifi",
        "SDM630-wifi",
    ],
)
async def test_system_set(model: str, snapshot: SnapshotAssertion, aresponses):
    """Test system set."""

    aresponses.add(
        "example.com",
        "/api/v1/system",
        "PUT",
        aresponses.Response(
            text=load_fixtures(f"{model}/system.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        system = await api.system(cloud_enabled=True)
        assert system
        assert system == snapshot

        await api.close()


async def test_system_set_unsupported_arguments():
    """Test system set when no arguments are given."""

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        with pytest.raises(UnsupportedError):
            await api.system(api_v1_enabled=True)


async def test_system_routes_brightness_to_state(aresponses):
    """Test system sets brightness to state."""

    aresponses.add(
        "example.com",
        "/api/v1/state",
        "PUT",
        aresponses.Response(
            text=load_fixtures("HWE-SKT/state_brightness.json"),
            status=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
        ),
    )

    async with aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1("example.com", clientsession=session)

        system = await api.system(status_led_brightness_pct=100)
        assert system.status_led_brightness_pct == 100
        await api.close()


# pylint: disable=protected-access
async def test_request_handles_timeout():
    """Test request raises timeout when request takes too long."""

    api = HomeWizardEnergyV1("example.com")
    api._session = AsyncMock()
    api._session.request = AsyncMock(side_effect=asyncio.TimeoutError())

    with pytest.raises(RequestError):
        # pylint: disable=protected-access
        await api._request("api/v1/data")

    assert api._session.request.call_count == 3


async def test_close_when_out_of_scope():
    """Test close called when object goes out of scope."""
    api = HomeWizardEnergyV1("example.com")
    api.close = AsyncMock()

    async with api as hwe:
        assert hwe == api

    assert api.close.call_count == 1
