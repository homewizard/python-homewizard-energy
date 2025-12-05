"""Test for CombinedModels model."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import CombinedModels, Device, Measurement, State

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model"),
    [
        "HWE-P1",
        "HWE-SKT",
        "HWE-WTR",
        "HWE-KWH1",
        "HWE-KWH3",
        "SDM230-wifi",
        "SDM630-wifi",
    ],
)
async def test_combined_model(model: str, snapshot: SnapshotAssertion):
    """Test combined model."""
    device = Device.from_dict(json.loads(load_fixtures(f"{model}/device.json")))
    measurement = Measurement.from_dict(json.loads(load_fixtures(f"{model}/data.json")))
    combined = CombinedModels(
        device=device, measurement=measurement, state=None, system=None
    )
    assert snapshot == combined


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
