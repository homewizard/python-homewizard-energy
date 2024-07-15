"""Test for HomeWizard Energy Models."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy import Data, Device, State, System

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


async def test_device_as_dict():
    """Test Device model as dict."""
    data = Device.from_dict(json.loads(load_fixtures("HWE-SKT/device.json")))
    assert data

    assert data["product_type"] == "HWE-SKT"

    count = 0
    # pylint does not detect __iter__ implementation via decorator
    # pylint: disable=not-an-iterable
    for value in data:
        if value is not None:
            count += 1
    assert count == 5


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
                "data_invalid_external_ean",
            ],
        ),
        ("HWE-SKT", ["data"]),
        ("HWE-WTR", ["data"]),
        ("HWE-KWH1", ["data"]),
        ("HWE-KWH3", ["data"]),
        ("SDM230-wifi", ["data"]),
        ("SDM630-wifi", ["data"]),
    ],
)
async def test_data(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Data model."""
    for fixture in fixtures:
        data = Data.from_dict(json.loads(load_fixtures(f"{model}/{fixture}.json")))
        assert data

        assert snapshot == data


async def test_data_as_dict():
    """Test Data model as dict."""
    data = Data.from_dict(json.loads(load_fixtures("HWE-SKT/data.json")))
    assert data

    assert data["wifi_ssid"] == "My Wi-Fi"

    count = 0
    # pylint does not detect __iter__ implementation via decorator
    # pylint: disable=not-an-iterable
    for value in data:
        if value is not None:
            count += 1
    assert (
        count == 8
    )  # 6 values + auto-filled 'total_power_import_kwh' and 'total_power_export_kwh'


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


async def test_state_as_dict():
    """Test State model as dict."""
    data = State.from_dict(json.loads(load_fixtures("HWE-SKT/state_all.json")))
    assert data

    assert data["brightness"] == 255

    count = 0
    # pylint does not detect __iter__ implementation via decorator
    # pylint: disable=not-an-iterable
    for value in data:
        if value is not None:
            count += 1
    assert count == 3


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


async def test_system_as_dict():
    """Test System model as dict."""
    data = System.from_dict(json.loads(load_fixtures("HWE-SKT/system.json")))
    assert data

    assert data["cloud_enabled"] is True

    count = 0
    # pylint does not detect __iter__ implementation via decorator
    # pylint: disable=not-an-iterable
    for value in data:
        if value is not None:
            count += 1
    assert count == 1
