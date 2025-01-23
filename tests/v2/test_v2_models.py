"""Test for HomeWizard Energy Models."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import Device, Measurement, System, SystemUpdate

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["device"]),
        ("HWE-BAT", ["device"]),
    ],
)
async def test_device(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Device model."""
    for fixture in fixtures:
        data = Device.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data

        assert snapshot == data


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            [
                "measurement_1_phase_no_gas",
                "measurement_3_phase_with_gas_with_watermeter",
                "measurement_invalid_ean",
                "measurement_invalid_external",
            ],
        ),
        (
            "HWE-BAT",
            [
                "measurement",
            ],
        ),
    ],
)
async def test_measurement(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Measurement model."""
    for fixture in fixtures:
        data = Measurement.from_dict(
            json.loads(load_fixtures(f"{model}/{fixture}.json"))
        )
        assert data

        assert snapshot == data


async def test_measurement_ignores_invalid_tariff():
    """Test Measurement model ignores invalid tariff."""

    measurement = Measurement.from_dict({"tariff": 5432})
    assert measurement
    assert measurement.tariff is None


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["system"]),
        ("HWE-BAT", ["system"]),
    ],
)
async def test_system(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test System model."""
    for fixture in fixtures:
        data = System.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data

        assert snapshot == data


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
    ("model", "supports_state", "supports_identify", "supports_cloud_enable"),
    [
        ("HWE-P1", False, True, True),
        ("HWE-BAT", False, True, False),
    ],
)
async def test_device_support_functions(
    model: str,
    supports_state: bool,
    supports_identify: bool,
    supports_cloud_enable: bool,
):
    """Test Device model support functions."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device

    assert device.supports_state() == supports_state
    assert device.supports_identify() == supports_identify
    assert device.supports_cloud_enable() == supports_cloud_enable
    assert device.supports_reboot() is True  # Always True for v2
