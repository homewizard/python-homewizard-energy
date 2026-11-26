"""Test the helper functions."""

import asyncio
import ssl
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from homewizard_energy import (
    _get_certificate_product_id,
    _get_v2_product_id,
    has_v2_api,
)
from homewizard_energy.v2 import create_ssl_context

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
    """Mock the product type identifier of a device that serves the v2 API."""
    with patch(
        "homewizard_energy._get_v2_product_id",
        new=AsyncMock(return_value="p1dongle"),
    ) as mock:
        yield mock


@pytest.fixture(name="mock_connection")
def fixture_mock_connection() -> Generator[tuple[AsyncMock, MagicMock, MagicMock]]:
    """Mock the HTTPS connection to a P1 Meter that serves the v2 API."""
    reader = MagicMock()
    reader.readline = AsyncMock(return_value=b"HTTP/1.1 401 Unauthorized\r\n")
    writer = MagicMock()
    writer.get_extra_info.return_value = _peercert("appliance/p1dongle/5c2fafaabbcc")
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()

    with patch(
        "homewizard_energy.asyncio.open_connection",
        new=AsyncMock(return_value=(reader, writer)),
    ) as mock_open_connection:
        yield mock_open_connection, reader, writer


@pytest.mark.parametrize(
    "product_id",
    ["p1dongle", "energysocket", "energymeter", "battery", "generic"],
)
async def test_has_v2_api_true(mock_product_id, product_id):
    """Test if has_v2_api returns True for a supported v2 device."""
    mock_product_id.return_value = product_id

    assert await has_v2_api("example.com") is True
    mock_product_id.assert_awaited_once_with("example.com")


@pytest.mark.parametrize(
    "product_id",
    ["watermeter", "display", "unknown", None],
)
async def test_has_v2_api_unsupported_model(mock_product_id, product_id):
    """Test if has_v2_api returns False for a v2 device that is not supported."""
    mock_product_id.return_value = product_id

    assert await has_v2_api("example.com") is False


@pytest.mark.parametrize(
    "exception",
    [
        ssl.SSLCertVerificationError,
        ssl.SSLError,
        ConnectionRefusedError,
        ConnectionResetError,
        TimeoutError,
        OSError,
    ],
)
async def test_has_v2_api_no_https(mock_product_id, exception):
    """Test if has_v2_api returns False without a valid HTTPS connection."""
    mock_product_id.side_effect = exception

    assert await has_v2_api("example.com") is False


async def test_has_v2_api_unexpected_error(mock_product_id):
    """Test if has_v2_api doesn't hide unexpected errors."""
    mock_product_id.side_effect = RuntimeError

    with pytest.raises(RuntimeError):
        await has_v2_api("example.com")


async def test_has_v2_api_websession_unused(mock_product_id):
    """Test if has_v2_api still accepts, but doesn't use, a websession."""
    session = AsyncMock(spec=ClientSession)

    assert await has_v2_api("example.com", session) is True
    assert not session.mock_calls
    mock_product_id.assert_awaited_once_with("example.com")


@pytest.mark.parametrize(
    ("product_type", "product_id"),
    [
        ("HWE-P1", "p1dongle"),
        ("HWE-SKT", "energysocket"),
        ("HWE-KWH1", "energymeter"),
        ("HWE-KWH3", "energymeter"),
        ("SDM230-wifi", "energymeter"),
        ("SDM630-wifi", "energymeter"),
        ("HWE-BAT", "battery"),
        ("HWE-BAT", "generic"),
        ("HWE-P1", "generic"),
    ],
)
async def test_has_v2_api_product_type(mock_product_id, product_type, product_id):
    """Test if has_v2_api returns True for a known, supported product type."""
    mock_product_id.return_value = product_id

    assert await has_v2_api("example.com", product_type=product_type) is True
    mock_product_id.assert_awaited_once_with("example.com")


@pytest.mark.parametrize("product_type", ["HWE-WTR", "HWE-DSP", "HWE-UNKNOWN"])
async def test_has_v2_api_product_type_unsupported(mock_product_id, product_type):
    """Test if has_v2_api skips the device for an unsupported product type."""
    mock_product_id.return_value = "generic"

    assert await has_v2_api("example.com", product_type=product_type) is False
    mock_product_id.assert_not_awaited()


@pytest.mark.parametrize("product_id", ["energysocket", "watermeter", None])
async def test_has_v2_api_product_type_mismatch(mock_product_id, product_id):
    """Test if has_v2_api returns False when the device has another product type."""
    mock_product_id.return_value = product_id

    assert await has_v2_api("example.com", product_type="HWE-P1") is False


async def test_has_v2_api_product_type_no_https(mock_product_id):
    """Test if has_v2_api returns False for a known type without HTTPS."""
    mock_product_id.side_effect = ConnectionRefusedError

    assert await has_v2_api("example.com", product_type="HWE-SKT") is False


@pytest.mark.parametrize(
    ("peercert", "expected"),
    [
        (_peercert("appliance/p1dongle/5c2fafaabbcc"), "p1dongle"),
        (_peercert("appliance/energysocket/5c2fafaabbcc"), "energysocket"),
        (_peercert("appliance/watermeter/5c2fafaabbcc"), "watermeter"),
        (_peercert("appliance/generic/3c39e7aabbcc"), "generic"),
        (_peercert("something/else"), None),
        (_peercert("device/p1dongle/5c2fafaabbcc"), None),
        ({"subject": ((("organizationName", "HomeWizard"),),)}, None),
        ({}, None),
        (None, None),
    ],
)
def test_get_certificate_product_id(peercert, expected):
    """Test reading the product type identifier from the device certificate."""
    assert _get_certificate_product_id(peercert) == expected


async def test_get_v2_product_id(mock_connection):
    """Test the product type identifier of a device that serves the v2 API."""
    mock_open_connection, reader, writer = mock_connection

    assert await _get_v2_product_id("192.168.1.2") == "p1dongle"

    mock_open_connection.assert_awaited_once()
    assert mock_open_connection.await_args.args == ("192.168.1.2", 443)
    context = mock_open_connection.await_args.kwargs["ssl"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is False
    writer.get_extra_info.assert_called_once_with("peercert")
    writer.write.assert_called_once_with(
        b"GET /api HTTP/1.1\r\nHost: 192.168.1.2\r\nConnection: close\r\n\r\n"
    )
    reader.readline.assert_awaited_once()
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()


async def test_get_v2_product_id_ipv6(mock_connection):
    """Test the Host header for an IPv6 address."""
    _, _, writer = mock_connection

    assert await _get_v2_product_id("fe80::1") == "p1dongle"

    writer.write.assert_called_once_with(
        b"GET /api HTTP/1.1\r\nHost: [fe80::1]\r\nConnection: close\r\n\r\n"
    )


@pytest.mark.parametrize(
    "status_line",
    [
        b"HTTP/1.1 404 Not Found\r\n",
        b"HTTP/1.1 200 OK\r\n",
        b"HTTP/1.1\r\n",
        b"",
    ],
)
async def test_get_v2_product_id_no_v2_api(mock_connection, status_line):
    """Test a device with a valid certificate, but without the v2 API."""
    _, reader, writer = mock_connection
    reader.readline.return_value = status_line

    assert await _get_v2_product_id("example.com") is None
    writer.close.assert_called_once()


@pytest.mark.parametrize(
    "peercert",
    [_peercert("something/else"), {}, None],
)
async def test_get_v2_product_id_unknown_certificate(mock_connection, peercert):
    """Test a certificate without product type identifier skips the request."""
    _, reader, writer = mock_connection
    writer.get_extra_info.return_value = peercert

    assert await _get_v2_product_id("example.com") is None
    writer.write.assert_not_called()
    reader.readline.assert_not_awaited()
    writer.close.assert_called_once()


@pytest.mark.parametrize(
    "exception",
    [ssl.SSLError, ConnectionResetError, asyncio.TimeoutError],
)
async def test_get_v2_product_id_close_error(mock_connection, exception):
    """Test errors while closing the connection are ignored."""
    _, _, writer = mock_connection
    writer.wait_closed.side_effect = exception

    assert await _get_v2_product_id("example.com") == "p1dongle"


@pytest.mark.parametrize(
    ("mock_name", "exception"),
    [
        ("readline", ConnectionResetError),
        ("readline", asyncio.TimeoutError),
        ("drain", ConnectionResetError),
    ],
)
async def test_get_v2_product_id_closes_on_error(mock_connection, mock_name, exception):
    """Test the connection is closed when the request fails."""
    _, reader, writer = mock_connection
    getattr(
        reader if mock_name == "readline" else writer, mock_name
    ).side_effect = exception

    with pytest.raises(exception):
        await _get_v2_product_id("example.com")

    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()


def test_create_ssl_context_without_hostname():
    """Test the SSL context validates the certificate, but not the hostname."""
    context = create_ssl_context(False)

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is False
    assert context.get_ca_certs()


def test_create_ssl_context_with_hostname():
    """Test the SSL context validates the certificate and the hostname."""
    context = create_ssl_context(True)

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.hostname_checks_common_name is True
    assert context.get_ca_certs()
