"""Test for Device model."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import Device

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["device"]),
        ("HWE-KWH1", ["device"]),
        ("HWE-KWH3", ["device"]),
        ("HWE-BAT", ["device"]),
    ],
)
async def test_device(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Device model."""
    for fixture in fixtures:
        data = Device.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data
        assert snapshot == data


# pylint: disable=too-many-arguments,too-many-positional-arguments
@pytest.mark.parametrize(
    (
        "model",
        "supports_state",
        "supports_identify",
        "supports_cloud_enable",
        "supports_reboot",
        "supports_telegram",
    ),
    [
        ("HWE-P1", False, True, True, True, True),
        ("HWE-KWH1", False, False, True, True, False),
        ("HWE-KWH3", False, False, True, True, False),
        ("HWE-BAT", False, True, False, False, False),
    ],
)
async def test_device_support_functions(
    model: str,
    supports_state: bool,
    supports_identify: bool,
    supports_cloud_enable: bool,
    supports_reboot: bool,
    supports_telegram: bool,
):
    """Test Device model support functions."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device
    assert device.supports_state() == supports_state
    assert device.supports_identify() == supports_identify
    assert device.supports_cloud_enable() == supports_cloud_enable
    assert device.supports_reboot() == supports_reboot
    assert device.supports_telegram() == supports_telegram
