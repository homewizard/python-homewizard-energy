"""Test for HomeWizard Energy Models."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import (
    Batteries,
    BatteriesUpdate,
    Device,
    Measurement,
    System,
    SystemUpdate,
)

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
            "HWE-KWH1",
            [
                "measurement",
            ],
        ),
        (
            "HWE-KWH3",
            [
                "measurement",
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
        ("HWE-KWH1", ["system"]),
        ("HWE-KWH3", ["system"]),
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
    ("model", "fixtures"),
    [
        ("HWE-P1", ["batteries"]),
        ("HWE-KWH1", ["batteries"]),
        ("HWE-KWH3", ["batteries"]),
    ],
)
async def test_batteries(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Batteries model."""
    for fixture in fixtures:
        data = Batteries.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data

        assert snapshot == data


@pytest.mark.parametrize(
    ("mode"),
    [
        Batteries.Mode.ZERO,
        Batteries.Mode.TO_FULL,
        Batteries.Mode.STANDBY,
    ],
)
async def test_batteries_update(
    mode: Batteries.Mode,
    snapshot: SnapshotAssertion,
):
    """Test System update."""
    data = BatteriesUpdate(
        mode=mode,
    )
    assert snapshot == data.to_dict()


@pytest.mark.parametrize(
    ("model", "supports_state"),
    [
        ("HWE-P1", False),
        ("HWE-KWH1", False),
        ("HWE-KWH3", False),
        ("HWE-BAT", False),
    ],
)
async def test_device_supports_state(model: str, supports_state: bool):
    """Test Device model supports_state function."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device.supports_state() == supports_state


@pytest.mark.parametrize(
    ("model", "supports_identify"),
    [
        ("HWE-P1", True),
        ("HWE-KWH1", False),
        ("HWE-KWH3", False),
        ("HWE-BAT", True),
    ],
)
async def test_device_supports_identify(model: str, supports_identify: bool):
    """Test Device model supports_identify function."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device.supports_identify() == supports_identify


@pytest.mark.parametrize(
    ("model", "supports_cloud_enable"),
    [
        ("HWE-P1", True),
        ("HWE-KWH1", True),
        ("HWE-KWH3", True),
        ("HWE-BAT", False),
    ],
)
async def test_device_supports_cloud_enable(model: str, supports_cloud_enable: bool):
    """Test Device model supports_cloud_enable function."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device.supports_cloud_enable() == supports_cloud_enable


@pytest.mark.parametrize(
    ("model", "supports_reboot"),
    [
        ("HWE-P1", True),
        ("HWE-KWH1", True),
        ("HWE-KWH3", True),
        ("HWE-BAT", False),
    ],
)
async def test_device_supports_reboot(model: str, supports_reboot: bool):
    """Test Device model supports_reboot function."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device.supports_reboot() == supports_reboot


@pytest.mark.parametrize(
    ("model", "supports_telegram"),
    [
        ("HWE-P1", True),
        ("HWE-KWH1", False),
        ("HWE-KWH3", False),
        ("HWE-BAT", False),
    ],
)
async def test_device_supports_telegram(model: str, supports_telegram: bool):
    """Test Device model supports_telegram function."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device.supports_telegram() == supports_telegram


@pytest.mark.parametrize(
    ("model", "supports_led_brightness"),
    [
        ("HWE-P1", True),
        ("HWE-KWH1", False),
        ("HWE-KWH3", False),
        ("HWE-BAT", True),
    ],
)
async def test_device_supports_led_brightness(
    model: str, supports_led_brightness: bool
):
    """Test Device model supports_led_brightness function."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device.supports_led_brightness() == supports_led_brightness
