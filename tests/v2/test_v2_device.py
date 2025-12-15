"""Test for Device model."""

import json

import pytest
from awesomeversion import AwesomeVersion
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.const import Model
from homewizard_energy.models import Batteries, Device

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


@pytest.mark.parametrize(
    "product_type,api_version,expected_modes",
    [  # Devices that do not support batteries
        (Model.ENERGY_SOCKET, "2.2.0", None),
        (Model.WATER_METER, "2.2.0", None),
        # Devices that support batteries, API < 2.2.0
        (
            Model.P1_METER,
            "2.1.0",
            [Batteries.Mode.ZERO, Batteries.Mode.TO_FULL, Batteries.Mode.STANDBY],
        ),
        (
            Model.ENERGY_METER_1_PHASE,
            "2.1.0",
            [Batteries.Mode.ZERO, Batteries.Mode.TO_FULL, Batteries.Mode.STANDBY],
        ),
        (
            Model.ENERGY_METER_3_PHASE,
            "2.1.0",
            [Batteries.Mode.ZERO, Batteries.Mode.TO_FULL, Batteries.Mode.STANDBY],
        ),
        (
            Model.ENERGY_METER_EASTRON_SDM230,
            "2.1.0",
            [Batteries.Mode.ZERO, Batteries.Mode.TO_FULL, Batteries.Mode.STANDBY],
        ),
        (
            Model.ENERGY_METER_EASTRON_SDM630,
            "2.1.0",
            [Batteries.Mode.ZERO, Batteries.Mode.TO_FULL, Batteries.Mode.STANDBY],
        ),
        # Devices that support batteries, API >= 2.2.0
        (
            Model.P1_METER,
            "2.2.0",
            [
                Batteries.Mode.ZERO,
                Batteries.Mode.TO_FULL,
                Batteries.Mode.STANDBY,
                Batteries.Mode.ZERO_CHARGE_ONLY,
                Batteries.Mode.ZERO_DISCHARGE_ONLY,
            ],
        ),
        (
            Model.ENERGY_METER_1_PHASE,
            "2.2.0",
            [
                Batteries.Mode.ZERO,
                Batteries.Mode.TO_FULL,
                Batteries.Mode.STANDBY,
                Batteries.Mode.ZERO_CHARGE_ONLY,
                Batteries.Mode.ZERO_DISCHARGE_ONLY,
            ],
        ),
        (
            Model.ENERGY_METER_3_PHASE,
            "2.2.0",
            [
                Batteries.Mode.ZERO,
                Batteries.Mode.TO_FULL,
                Batteries.Mode.STANDBY,
                Batteries.Mode.ZERO_CHARGE_ONLY,
                Batteries.Mode.ZERO_DISCHARGE_ONLY,
            ],
        ),
        (
            Model.ENERGY_METER_EASTRON_SDM230,
            "2.2.0",
            [
                Batteries.Mode.ZERO,
                Batteries.Mode.TO_FULL,
                Batteries.Mode.STANDBY,
                Batteries.Mode.ZERO_CHARGE_ONLY,
                Batteries.Mode.ZERO_DISCHARGE_ONLY,
            ],
        ),
        (
            Model.ENERGY_METER_EASTRON_SDM630,
            "2.2.0",
            [
                Batteries.Mode.ZERO,
                Batteries.Mode.TO_FULL,
                Batteries.Mode.STANDBY,
                Batteries.Mode.ZERO_CHARGE_ONLY,
                Batteries.Mode.ZERO_DISCHARGE_ONLY,
            ],
        ),
    ],
)
def test_supported_battery_modes(product_type, api_version, expected_modes):
    """Test supported_battery_modes method of Device."""
    device = Device(
        product_name="Test Device",
        product_type=product_type,
        serial="1234567890",
        api_version=AwesomeVersion(api_version),
        firmware_version="1.0.0",
    )
    result = device.supported_battery_modes()
    if expected_modes is None:
        assert result is None
    else:
        assert result == expected_modes
