"""Test for System model."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import System

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


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
