"""Test for HomeWizard Energy."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy import HomeWizardEnergyV2
from homewizard_energy.errors import (
    DisabledError,
    RequestError,
    ResponseError,
    UnauthorizedError,
)
from homewizard_energy.models import SystemUpdate

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]

### Device tests ###


async def test_class_returns_host():
    """Test class returns host."""

    async with HomeWizardEnergyV2("example.com") as api:
        assert api.host == "example.com"


async def test_device_without_authentication():
    """Test device request is rejected when no authentication is provided."""

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(UnauthorizedError):
            await api.device()


async def test_device_with_invalid_authentication(aresponses):
    """Test device request is unsuccessful when invalid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=401,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:unauthorized"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(UnauthorizedError):
            await api.device()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["device"]),
    ],
)
async def test_device_with_valid_authentication(
    model: str, fixtures: list[str], snapshot: SnapshotAssertion, aresponses
):
    """Test device request is successful when valid authentication is provided."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json"},
            ),
        )

        async with HomeWizardEnergyV2("example.com", token="token") as api:
            device = await api.device()

            assert device
            assert device.product_type == model

            assert device == snapshot


### Measurement tests ###


async def test_measurement_without_authentication():
    """Test measurement request is rejected when no authentication is provided."""

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(UnauthorizedError):
            await api.measurement()


async def test_measurement_with_invalid_authentication(aresponses):
    """Test measurement request is unsuccessful when invalid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/measurement",
        "GET",
        aresponses.Response(
            status=401,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:unauthorized"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(UnauthorizedError):
            await api.measurement()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            [
                "measurement_1_phase_no_gas",
                "measurement_3_phase_with_gas_with_watermeter",
            ],
        ),
    ],
)
async def test_measurement_with_valid_authentication(
    model: str, fixtures: list[str], snapshot: SnapshotAssertion, aresponses
):
    """Test measurement request is successful when valid authentication is provided."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api/measurement",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json"},
            ),
        )

        async with HomeWizardEnergyV2("example.com", token="token") as api:
            measurement = await api.measurement()
            assert measurement is not None
            assert measurement == snapshot


### System tests ###


async def test_system_without_authentication():
    """Test system request is rejected when no authentication is provided."""

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(UnauthorizedError):
            await api.system()


async def test_system_with_invalid_authentication(aresponses):
    """Test system request is unsuccessful when invalid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system",
        "GET",
        aresponses.Response(
            status=401,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:unauthorized"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(UnauthorizedError):
            await api.system()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["system"]),
    ],
)
async def test_system_with_valid_authentication(
    model: str, fixtures: list[str], snapshot: SnapshotAssertion, aresponses
):
    """Test system request is successful when valid authentication is provided."""

    for fixture in fixtures:
        aresponses.add(
            "example.com",
            "/api/system",
            "GET",
            aresponses.Response(
                text=load_fixtures(f"{model}/{fixture}.json"),
                status=200,
                headers={"Content-Type": "application/json"},
            ),
        )

        async with HomeWizardEnergyV2("example.com", token="token") as api:
            system = await api.system()
            assert system is not None
            assert system == snapshot


async def test_system_set_with_valid_authentication(aresponses):
    """Test system set request is successful when valid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"cloud_enabled": true}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        data = await api.system(update=SystemUpdate(cloud_enabled=True))
        assert data is not None
        assert data.cloud_enabled is True


async def test_system_returns_unexpected_response(aresponses):
    """Test system set request is successful when valid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system",
        "GET",
        aresponses.Response(
            status=500,
            headers={"Content-Type": "application/json"},
            text='{"error": "server:error"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(RequestError) as e:
            await api.system()
            assert str(e.value) == "server:error"


### Identify tests ###


async def test_identify_without_authentication():
    """Test identify request is rejected when no authentication is provided."""

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(UnauthorizedError):
            await api.identify()


async def test_identify_with_invalid_authentication(aresponses):
    """Test identify request is unsuccessful when invalid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system/identify",
        "PUT",
        aresponses.Response(
            status=401,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:unauthorized"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(UnauthorizedError):
            await api.identify()


async def test_identify_with_authentication(aresponses):
    """Test identify request is successful when authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system/identify",
        "PUT",
        aresponses.Response(
            status=204,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        data = await api.identify()
        assert data is None


### Reboot tests ###


async def test_reboot_without_authentication():
    """Test reboot request is rejected when no authentication is provided."""

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(UnauthorizedError):
            await api.reboot()


async def test_reboot_with_invalid_authentication(aresponses):
    """Test reboot request is unsuccessful when invalid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system/reboot",
        "PUT",
        aresponses.Response(
            status=401,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:unauthorized"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(UnauthorizedError):
            await api.reboot()


async def test_reboot_with_authentication(aresponses):
    """Test reboot request is successful when authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/system/reboot",
        "PUT",
        aresponses.Response(
            status=204,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        data = await api.reboot()
        assert data is None


### Get token tests ###


async def test_get_token_without_permission(aresponses):
    """Test get token request is rejected when no permission, user must authorize."""

    aresponses.add(
        "example.com",
        "/api/user",
        "POST",
        aresponses.Response(
            status=403,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:creation-not-enabled"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(DisabledError):
            await api.get_token("name")


async def test_get_token_with_permission(aresponses):
    """Test get token request accepted."""

    aresponses.add(
        "example.com",
        "/api/user",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"token": "new_token", "name": "local/name"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com") as api:
        token = await api.get_token("name")
        assert token == "new_token"


async def test_get_token_returns_unexpected_response_code(aresponses):
    """Test get token request is successful when valid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/user",
        "POST",
        aresponses.Response(
            status=500,
            headers={"Content-Type": "application/json"},
            text='{"error": "server:error"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(RequestError) as e:
            await api.get_token("name")
            assert str(e.value) == "server:error"


async def test_get_token_returns_unexpected_response_data(aresponses):
    """Test get token request is successful when valid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/user",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:error"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(ResponseError) as e:
            await api.get_token("name")
            assert str(e.value) == "user:error"


async def test_delete_token_without_authentication():
    """Test delete token request is rejected when no authentication is provided."""

    async with HomeWizardEnergyV2("example.com") as api:
        with pytest.raises(UnauthorizedError):
            await api.delete_token()


async def test_delete_token_with_invalid_authentication(aresponses):
    """Test delete token request is unsuccessful when invalid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/user",
        "DELETE",
        aresponses.Response(
            status=401,
            headers={"Content-Type": "application/json"},
            text='{"error": "user:unauthorized"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(UnauthorizedError):
            await api.delete_token()


async def test_delete_token_with_authentication(aresponses):
    """Test delete_token request is successful when authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/user",
        "DELETE",
        aresponses.Response(
            status=204,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        await api.delete_token()
        assert api._token is None  # pylint: disable=protected-access


async def test_delete_token_from_other_user_with_authentication(aresponses):
    """Test delete_token request is successful when authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/user",
        "DELETE",
        aresponses.Response(
            status=204,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        await api.delete_token(name="local/other")
        assert api._token == "token"  # pylint: disable=protected-access


async def test_delete_token_returns_unexpected_response_code(aresponses):
    """Test delete token request is successful when valid authentication is provided."""

    aresponses.add(
        "example.com",
        "/api/user",
        "DELETE",
        aresponses.Response(
            status=500,
            headers={"Content-Type": "application/json"},
            text='{"error": "server:error"}',
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token") as api:
        with pytest.raises(RequestError) as e:
            await api.delete_token()
            assert str(e.value) == "server:error"


### Generic request tests ###


# pylint: disable=protected-access
async def test_request_handles_timeout():
    """Test request times out when request takes too long."""
    async with HomeWizardEnergyV2("example.com", token="token") as api:
        api._session = AsyncMock()
        api._session.request = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(RequestError):
            await api.device()

        assert api._session.request.call_count == 3


async def test_request_with_identifier_sets_common_name(aresponses):
    """Test request with identifier sets common name."""

    device = load_fixtures("HWE-P1/device.json")
    device.replace("HWE-P1", "NEW-DEVICE")

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            text=device,
            status=200,
            headers={"Content-Type": "application/json"},
        ),
    )

    async with HomeWizardEnergyV2("example.com", token="token", identifier="id") as api:
        data = await api.device()
        assert data is not None
