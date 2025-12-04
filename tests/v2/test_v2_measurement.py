"""Test for Measurement model."""

import json

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import Measurement

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model", "fixtures"),
    [
        (
            "HWE-P1",
            [
                "measurement_1_phase_no_gas",
                "measurement_3_phase_with_gas_with_watermeter",
                "measurement_invalid_ean",
                "measurement_invalid_external",
            ],
        ),
        ("HWE-KWH1", ["measurement"]),
        ("HWE-KWH3", ["measurement"]),
        ("HWE-BAT", ["measurement"]),
    ],
)
async def test_measurement(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Measurement model."""
    for fixture in fixtures:
        data = Measurement.from_dict(
            json.loads(load_fixtures(f"{model}/{fixture}.json"))
        )
        assert data
        assert snapshot == data


async def test_measurement_ignores_invalid_tariff():
    """Test Measurement model ignores invalid tariff."""
    measurement = Measurement.from_dict({"tariff": 5432})
    assert measurement
    assert measurement.tariff is None
