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
    """Test Batteries update."""
    data = BatteriesUpdate(
        mode=mode,
    )
    assert snapshot == data.to_dict()
