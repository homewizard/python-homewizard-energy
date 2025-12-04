"""Test for State model."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import State

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


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
