"""Test for HomeWizard Energy Models."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy import Data, Decryption, Device, State, System

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    "fixture",
    [
        "device.json",
        "device_energysocket.json",
        "device_extra_parameters.json",
        "device_invalid_api.json",
    ],
)
async def test_device(fixture: str, snapshot: SnapshotAssertion):
    """Test Device model."""
    data = Device.from_dict(json.loads(load_fixtures(fixture)))
    assert data

    assert snapshot == data


@pytest.mark.parametrize(
    "fixture",
    [
        "data_energysocket.json",
        "data_kwh_single_phase.json",
        "data_kwh_three_phase.json",
        "data_p1_full.json",
        "data_p1_no_gas.json",
        "data_p1_single_phase.json",
        "data_p1.json",
        "data_watermeter.json",
    ],
)
async def test_data(fixture: str, snapshot: SnapshotAssertion):
    """Test Data model."""
    data = Data.from_dict(json.loads(load_fixtures(fixture)))
    assert data

    assert snapshot == data


@pytest.mark.parametrize(
    "fixture",
    [
        "decryption.json",
    ],
)
async def test_decryption(fixture: str, snapshot: SnapshotAssertion):
    """Test Decryption model."""
    data = Decryption.from_dict(json.loads(load_fixtures(fixture)))
    assert data

    assert snapshot == data


@pytest.mark.parametrize(
    "fixture",
    [
        "state.json",
        "state_switch_lock_and_brightness.json",
    ],
)
async def test_state(fixture: str, snapshot: SnapshotAssertion):
    """Test State model."""
    data = State.from_dict(json.loads(load_fixtures(fixture)))
    assert data

    assert snapshot == data


@pytest.mark.parametrize(
    "fixture",
    [
        "system_cloud_disabled.json",
        "system_cloud_enabled.json",
    ],
)
async def test_system(fixture: str, snapshot: SnapshotAssertion):
    """Test System model."""
    data = System.from_dict(json.loads(load_fixtures(fixture)))
    assert data

    assert snapshot == data
