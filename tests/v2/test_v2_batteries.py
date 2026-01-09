"""Test for Batteries model and BatteriesUpdate."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import Batteries, BatteriesUpdate

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        ("HWE-P1", ["batteries_2_1_0", "batteries_2_2_0"]),
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


def test_batteries_battery_count_optional():
    """Test Batteries model with and without battery_count."""
    b1 = Batteries(
        mode=Batteries.Mode.ZERO,
        power_w=100.0,
        target_power_w=200.0,
        max_consumption_w=300.0,
        max_production_w=400.0,
        battery_count=None,
    )
    b2 = Batteries(
        mode=Batteries.Mode.TO_FULL,
        power_w=110.0,
        target_power_w=210.0,
        max_consumption_w=310.0,
        max_production_w=410.0,
        battery_count=2,
    )
    assert b1.battery_count is None
    assert b2.battery_count == 2


@pytest.mark.parametrize(
    "mode, expected_mode, expected_permissions",
    [
        (
            Batteries.Mode.ZERO,
            Batteries.Mode.ZERO,
            [
                Batteries.Permissions.CHARGE_ALLOWED,
                Batteries.Permissions.DISCHARGE_ALLOWED,
            ],
        ),
        (
            Batteries.Mode.ZERO_CHARGE_ONLY,
            Batteries.Mode.ZERO,
            [Batteries.Permissions.CHARGE_ALLOWED],
        ),
        (
            Batteries.Mode.ZERO_DISCHARGE_ONLY,
            Batteries.Mode.ZERO,
            [Batteries.Permissions.DISCHARGE_ALLOWED],
        ),
        (Batteries.Mode.TO_FULL, Batteries.Mode.TO_FULL, None),
        (Batteries.Mode.STANDBY, Batteries.Mode.STANDBY, []),
    ],
)
def test_batteries_update_modes_and_permissions(
    mode, expected_mode, expected_permissions
):
    """Test BatteriesUpdate for all modes and permissions."""
    update = BatteriesUpdate.from_mode(mode=mode)

    assert update.mode == expected_mode
    assert update.permissions == expected_permissions


@pytest.mark.parametrize(
    "mode, permissions, expected_mode",
    [
        (
            Batteries.Mode.ZERO,
            [
                Batteries.Permissions.CHARGE_ALLOWED,
                Batteries.Permissions.DISCHARGE_ALLOWED,
            ],
            Batteries.Mode.ZERO,
        ),
        (
            Batteries.Mode.ZERO,
            [Batteries.Permissions.CHARGE_ALLOWED],
            Batteries.Mode.ZERO_CHARGE_ONLY,
        ),
        (
            Batteries.Mode.ZERO,
            [Batteries.Permissions.DISCHARGE_ALLOWED],
            Batteries.Mode.ZERO_DISCHARGE_ONLY,
        ),
        (Batteries.Mode.ZERO, [], Batteries.Mode.STANDBY),
        (Batteries.Mode.STANDBY, [], Batteries.Mode.STANDBY),
        (Batteries.Mode.TO_FULL, [], Batteries.Mode.TO_FULL),
    ],
)
def test_set_mode_based_on_permissions(mode, permissions, expected_mode):
    """Test setting Batteries mode based on permissions."""
    model = Batteries.from_dict(
        {
            "mode": mode,
            "permissions": permissions,
            "power_w": 0.0,
            "target_power_w": 0.0,
            "max_consumption_w": 0.0,
            "max_production_w": 0.0,
        }
    )
    assert model.mode == expected_mode


def test_set_batteries_update_with_invalid_permissions_raises():
    """Test BatteriesUpdate with invalid permissions raises ValueError."""
    with pytest.raises(ValueError):
        BatteriesUpdate.from_mode(
            mode="invalid_mode",  # mypy: ignore [arg-type]
        )
