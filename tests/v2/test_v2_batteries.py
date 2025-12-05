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
    "mode,permissions",
    [
        (
            Batteries.Mode.ZERO,
            [
                Batteries.Permissions.CHARGE_ALLOWED,
                Batteries.Permissions.DISCHARGE_ALLOWED,
            ],
        ),
        (Batteries.Mode.ZERO_CHARGE_ONLY, [Batteries.Permissions.CHARGE_ALLOWED]),
        (Batteries.Mode.ZERO_DISCHARGE_ONLY, [Batteries.Permissions.DISCHARGE_ALLOWED]),
        (Batteries.Mode.TO_FULL, None),
        (Batteries.Mode.STANDBY, []),
    ],
)
def test_batteries_update_modes_and_permissions(mode, permissions):
    """Test BatteriesUpdate for all modes and permissions."""
    if permissions is not None:
        update = BatteriesUpdate(mode=mode, permissions=permissions)
    else:
        update = BatteriesUpdate(mode=mode)
    assert update.mode == mode
    if permissions is not None:
        assert update.permissions in (permissions, [])


def test_batteries_update_invalid_mode():
    """Test BatteriesUpdate with invalid mode raises ValueError."""
    with pytest.raises(ValueError):
        BatteriesUpdate.from_mode(mode="INVALID_MODE")
