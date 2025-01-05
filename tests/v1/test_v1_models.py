"""Test for HomeWizard Energy Models."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import CombinedModels, Device, Measurement, State, System

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["device"]),
        ("HWE-SKT", ["device"]),
        ("HWE-WTR", ["device"]),
        ("HWE-KWH1", ["device"]),
        ("HWE-KWH3", ["device"]),
        ("SDM230-wifi", ["device"]),
        ("SDM630-wifi", ["device"]),
    ],
)
async def test_device(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Device model."""
    for fixture in fixtures:
        data = Device.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data

        assert snapshot == data


async def test_combined_remaps_legacy_wifi_ssid_to_system(snapshot: SnapshotAssertion):
    """Test CombinedModels model remaps wifi_ssid to system."""
    device = Device.from_dict(json.loads(load_fixtures("HWE-SKT/device.json")))
    measurement = Measurement.from_dict(json.loads(load_fixtures("HWE-SKT/data.json")))

    combined = CombinedModels(
        device=device, measurement=measurement, state=None, system=None
    )

    assert combined.system.wifi_ssid == measurement.wifi_ssid
    assert snapshot == combined


async def test_combined_remaps_legacy_brightness_to_system(snapshot: SnapshotAssertion):
    """Test CombinedModels model remaps wifi_ssid to system."""
    device = Device.from_dict(json.loads(load_fixtures("HWE-SKT/device.json")))
    state = State.from_dict(json.loads(load_fixtures("HWE-SKT/state_all.json")))

    combined = CombinedModels(device=device, measurement=None, state=state, system=None)

    assert combined.system.status_led_brightness_pct == state.brightness / 2.55
    assert snapshot == combined


@pytest.mark.parametrize(
    ("model", "supports_state", "supports_identify"),
    [
        ("HWE-P1", False, True),
        ("HWE-SKT", True, True),
        ("HWE-WTR", False, True),
        ("HWE-KWH1", False, False),
        ("HWE-KWH3", False, False),
        ("SDM230-wifi", False, False),
        ("SDM630-wifi", False, False),
    ],
)
async def test_device_support_functions(
    model: str, supports_state: bool, supports_identify: bool
):
    """Test Device model support functions."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    assert device

    assert device.supports_state() == supports_state
    assert device.supports_identify() == supports_identify


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            [
                "data_minimal",
                "data_all_data",
                "data_no_gas",
                "data_single_phase",
            ],
        ),
        ("HWE-SKT", ["data"]),
        ("HWE-WTR", ["data"]),
        ("HWE-KWH1", ["data"]),
        ("HWE-KWH3", ["data"]),
        ("SDM230-wifi", ["data"]),
        ("SDM630-wifi", ["data"]),
        (
            "exceptions",
            [
                "data_invalid_external_ean",
                "data_invalid_external_data",
            ],
        ),
    ],
)
async def test_data(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Measurement model."""
    for fixture in fixtures:
        data = Measurement.from_dict(
            json.loads(load_fixtures(f"{model}/{fixture}.json"))
        )
        assert data

        assert snapshot == data


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-SKT",
            ["state_all", "state_power_on", "state_switch_lock", "state_brightness"],
        ),
    ],
)
async def test_state(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test State model."""
    for fixture in fixtures:
        data = State.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data

        assert snapshot == data


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
