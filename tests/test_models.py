"""Test for HomeWizard Energy Models."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy import Data, Decryption, Device, State, System

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


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            ["data_minimal", "data_all_data", "data_no_gas", "data_single_phase"],
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


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["decryption"]),
    ],
)
async def test_decryption(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Decryption model."""
    for fixture in fixtures:
        data = Decryption.from_dict(
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
