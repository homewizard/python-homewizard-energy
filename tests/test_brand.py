"""Test for HomeWizard Energy Models."""

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.v1.brand import from_type

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model"),
    [
        ("HWE-P1"),
        ("HWE-SKT"),
        ("HWE-WTR"),
        ("HWE-KWH1"),
        ("HWE-KWH3"),
        ("SDM230-wifi"),
        ("SDM630-wifi"),
    ],
)
async def test_known_products(model: str, snapshot: SnapshotAssertion):
    """Test known products."""

    product = from_type(model)
    assert product is not None
    assert snapshot == product


@pytest.mark.parametrize(
    ("model"),
    [
        ("HWE-P1"),
        ("HWE-SKT"),
        ("HWE-WTR"),
        ("HWE-KWH1"),
        ("HWE-KWH3"),
        ("SDM230-wifi"),
        ("SDM630-wifi"),
    ],
)
async def test_known_product_strings(model: str, snapshot: SnapshotAssertion):
    """Test generating product strings."""

    product = from_type(model)
    assert product is not None
    assert snapshot == str(product)


@pytest.mark.parametrize(
    ("model"),
    [
        ("HWE-P2"),
        (None),
        ("WTR"),
        (""),
    ],
)
async def test_unknown_or_invalid_products(model: str, snapshot: SnapshotAssertion):
    """Test unknown or invalid products types."""

    product = from_type(model)
    assert product is None
    assert snapshot == product


@pytest.mark.parametrize(
    ("lhs", "rhs", "value"),
    [
        ("HWE-P1", "HWE-P1", True),
        ("HWE-P1", "HWE-SKT", False),
        ("HWE-P1", None, False),
        ("HWE-P1", "", False),
    ],
)
async def test_comparison_between_products(lhs: str, rhs: str, value: bool):
    """Test comparison between products."""

    lhs = from_type(lhs)
    rhs = from_type(rhs)
    assert (lhs == rhs) == value
