"""Test the helper functions."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from homewizard_energy import has_v2_api

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
    session.get = AsyncMock(side_effect=asyncio.TimeoutError)

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
