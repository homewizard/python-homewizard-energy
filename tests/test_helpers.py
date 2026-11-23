"""Test the helper functions."""

import asyncio
import ssl
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from homewizard_energy import (
    _certificate_ssl_context,
    _get_certificate_product_id,
    has_v2_api,
)

pytestmark = [pytest.mark.asyncio]


def _peercert(common_name: str) -> dict[str, Any]:
    """Build a certificate as returned by `SSLSocket.getpeercert()`."""
    return {
        "subject": (
            (("countryName", "NL"),),
            (("organizationName", "HomeWizard"),),
            (("commonName", common_name),),
        ),
    }


@pytest.fixture(name="mock_product_id")
def fixture_mock_product_id() -> Generator[AsyncMock]:
    """Mock the product type identifier read from the device certificate."""
    with patch(
        "homewizard_energy._get_certificate_product_id",
        new=AsyncMock(return_value="p1dongle"),
    ) as mock:
        yield mock


def _add_api_response(aresponses, status: int) -> None:
    """Add a response for the unauthenticated v2 /api endpoint."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=status,
        ),
    )


@pytest.mark.parametrize(
    "product_id",
    ["p1dongle", "energysocket", "energymeter", "battery"],
)
async def test_has_v2_api_true(aresponses, mock_product_id, product_id):
    """Test if has_v2_api returns True for a supported v2 device."""
    mock_product_id.return_value = product_id
    _add_api_response(aresponses, 401)

    async with ClientSession() as session:
        result = await has_v2_api("example.com", session)
        assert result is True

    mock_product_id.assert_awaited_once_with("example.com")


@pytest.mark.parametrize(
    "product_id",
    ["watermeter", "display", "unknown", None],
)
async def test_has_v2_api_unsupported_model(aresponses, mock_product_id, product_id):
    """Test if has_v2_api returns False for a v2 device that is not supported."""
    mock_product_id.return_value = product_id
    _add_api_response(aresponses, 401)

    async with ClientSession() as session:
        result = await has_v2_api("example.com", session)
        assert result is False


async def test_has_v2_api_certificate_error(aresponses, mock_product_id):
    """Test if has_v2_api returns False when the certificate can't be read."""
    mock_product_id.side_effect = ssl.SSLCertVerificationError
    _add_api_response(aresponses, 401)

    async with ClientSession() as session:
        result = await has_v2_api("example.com", session)
        assert result is False


async def test_has_v2_api_false(aresponses, mock_product_id):
    """Test if has_v2_api returns False for a non-v2 device."""
    _add_api_response(aresponses, 404)

    async with ClientSession() as session:
        result = await has_v2_api("example.com", session)
        assert result is False

    mock_product_id.assert_not_awaited()


async def test_has_v2_api_exception():
    """Test if has_v2_api returns False when an exception occurs."""
    session = AsyncMock()
    session.get = AsyncMock(side_effect=asyncio.TimeoutError)

    result = await has_v2_api("example.com", session)
    assert result is False


async def test_has_v2_api_own_session(aresponses, mock_product_id):
    """Test if has_v2_api opens and closes its own session."""
    _add_api_response(aresponses, 401)

    result = await has_v2_api("example.com")
    assert result is True

    mock_product_id.assert_awaited_once_with("example.com")


@pytest.mark.parametrize(
    ("peercert", "expected"),
    [
        (_peercert("appliance/p1dongle/5c2fafaabbcc"), "p1dongle"),
        (_peercert("appliance/energysocket/5c2fafaabbcc"), "energysocket"),
        (_peercert("appliance/watermeter/5c2fafaabbcc"), "watermeter"),
        (_peercert("something/else"), None),
        (_peercert("device/p1dongle/5c2fafaabbcc"), None),
        ({"subject": ((("organizationName", "HomeWizard"),),)}, None),
        ({}, None),
        (None, None),
    ],
)
async def test_get_certificate_product_id(peercert, expected):
    """Test reading the product type identifier from the device certificate."""
    writer = MagicMock()
    writer.get_extra_info.return_value = peercert

    with patch(
        "homewizard_energy.asyncio.open_connection",
        new=AsyncMock(return_value=(MagicMock(), writer)),
    ) as mock_open_connection:
        assert await _get_certificate_product_id("example.com") == expected

    mock_open_connection.assert_awaited_once()
    assert mock_open_connection.await_args.args == ("example.com", 443)
    assert mock_open_connection.await_args.kwargs["ssl"] is _certificate_ssl_context()
    writer.get_extra_info.assert_called_once_with("peercert")
    writer.close.assert_called_once()


async def test_get_certificate_product_id_closes_on_error():
    """Test the connection is closed when reading the certificate fails."""
    writer = MagicMock()
    writer.get_extra_info.side_effect = RuntimeError

    with (
        patch(
            "homewizard_energy.asyncio.open_connection",
            new=AsyncMock(return_value=(MagicMock(), writer)),
        ),
        pytest.raises(RuntimeError),
    ):
        await _get_certificate_product_id("example.com")

    writer.close.assert_called_once()


def test_certificate_ssl_context():
    """Test the SSL context validates the certificate but not the hostname."""
    context = _certificate_ssl_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is False
    assert context.get_ca_certs()
