"""Test the helper functions."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from homewizard_energy import get_verification_hostname, has_v2_api

pytestmark = [pytest.mark.asyncio]


async def test_has_v2_api_true(aresponses):
    """Test if has_v2_api returns True for a v2 device."""

    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=401,
        ),
    )

    async with ClientSession() as session:
        result = await has_v2_api("example.com", session)
        assert result is True


async def test_has_v2_api_false(aresponses):
    """Test if has_v2_api returns False for a non-v2 device."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=404,
        ),
    )

    async with ClientSession() as session:
        result = await has_v2_api("example.com", session)
        assert result is False


async def test_has_v2_api_exception():
    """Test if has_v2_api returns False when an exception occurs."""
    session = AsyncMock()
    session.request = AsyncMock(side_effect=asyncio.TimeoutError())

    result = await has_v2_api("example.com", session)
    assert result is False


async def test_has_v2_api_own_session(aresponses):
    """Test if has_v2_api opens and closes its own session."""
    aresponses.add(
        "example.com",
        "/api",
        "GET",
        aresponses.Response(
            status=401,
        ),
    )

    result = await has_v2_api("example.com")
    assert result is True


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("HWE-P1", "appliance/p1dongle/1234567890"),
        ("HWE-SKT", "appliance/energysocket/1234567890"),
        ("HWE-WTR", "appliance/watermeter/1234567890"),
        ("HWE-DSP", "appliance/display/1234567890"),
        ("HWE-KWH1", "appliance/energymeter/1234567890"),
        ("SDM230-wifi", "appliance/energymeter/1234567890"),
        ("HWE-KWH3", "appliance/energymeter/1234567890"),
        ("SDM630-wifi", "appliance/energymeter/1234567890"),
        ("HWE-BAT", "appliance/battery/1234567890"),
    ],
)
async def test_get_verification_hostname_returns_expected_identifier(
    model: str, expected: str
):
    """Test if get_verification_hostname returns the expected identifier."""
    result = get_verification_hostname(model, "1234567890")
    assert result == expected


def test_get_verification_hostname_raises_value_error():
    """Test if get_verification_hostname raises a ValueError for an unsupported model."""
    with pytest.raises(ValueError):
        get_verification_hostname("unsupported", "1234567890")
