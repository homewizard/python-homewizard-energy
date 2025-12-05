"""Test for System model."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import System, SystemUpdate

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("cloud_enabled", "status_led_brightness_pct", "api_v1_enabled"),
    [
        (True, None, None),
        (None, 100, None),
        (None, None, True),
        (True, 100, None),
        (True, None, True),
        (None, 100, True),
        (True, 100, True),
    ],
)
async def test_system_update(
    cloud_enabled: bool,
    status_led_brightness_pct: int,
    api_v1_enabled: bool,
    snapshot: SnapshotAssertion,
):
    """Test System update."""
    data = SystemUpdate(
        cloud_enabled=cloud_enabled,
        status_led_brightness_pct=status_led_brightness_pct,
        api_v1_enabled=api_v1_enabled,
    )
    assert snapshot == data.to_dict()


async def test_system_update_raises_when_none_set():
    """Test systemUpdate raises when all values are None."""
    update = SystemUpdate(
        cloud_enabled=None, status_led_brightness_pct=None, api_v1_enabled=None
    )

    with pytest.raises(ValueError):
        update.to_dict()


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["system"]),
        ("HWE-SKT", ["system"]),
        ("HWE-WTR", ["system"]),
        ("HWE-KWH1", ["system"]),
        ("HWE-KWH3", ["system"]),
        ("SDM230-wifi", ["system"]),
        ("SDM630-wifi", ["system"]),
    ],
)
async def test_system(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test System model."""
    for fixture in fixtures:
        data = System.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data
        assert snapshot == data
