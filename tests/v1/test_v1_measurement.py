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
                "data_minimal",
                "data",
                "data_no_gas",
                "data_single_phase",
            ],
        ),
        ("HWE-SKT", ["data"]),
        ("HWE-WTR", ["data"]),
        ("HWE-KWH1", ["data"]),
        ("HWE-KWH3", ["data"]),
        ("SDM230-wifi", ["data"]),
        ("SDM630-wifi", ["data"]),
        (
            "exceptions",
            [
                "data_invalid_external_ean",
                "data_invalid_external_data",
            ],
        ),
    ],
)
async def test_data(model: str, fixtures: str, snapshot: SnapshotAssertion):
    """Test Measurement model."""
    for fixture in fixtures:
        data = Measurement.from_dict(
            json.loads(load_fixtures(f"{model}/{fixture}.json"))
        )
        assert data
        assert snapshot == data


async def test_data_ignores_invalid_tariff():
    """Test Data model ignores invalid tariff."""
    measurement = Measurement.from_dict({"active_tariff": 5432})
    assert measurement
    assert measurement.tariff is None
