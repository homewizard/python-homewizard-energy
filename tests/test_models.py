"""Test the helper functions."""

import pytest
from syrupy.assertion import SnapshotAssertion

from homewizard_energy.models import Product, get_verification_hostname

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("HWE-P1", "appliance/p1dongle/1234567890"),
        ("HWE-SKT", "appliance/energysocket/1234567890"),
        ("HWE-WTR", "appliance/watermeter/1234567890"),
        ("HWE-DSP", "appliance/display/1234567890"),
        ("HWE-KWH1", "appliance/energymeter/1234567890"),
        ("SDM230-wifi", "appliance/energymeter/1234567890"),
        ("HWE-KWH3", "appliance/energymeter/1234567890"),
        ("SDM630-wifi", "appliance/energymeter/1234567890"),
        ("HWE-BAT", "appliance/battery/1234567890"),
    ],
)
async def test_get_verification_hostname_returns_expected_identifier(
    model: str, expected: str
):
    """Test if get_verification_hostname returns the expected identifier."""
    result = get_verification_hostname(model, "1234567890")
    assert result == expected


async def test_get_verification_hostname_raises_value_error():
    """Test if get_verification_hostname raises a ValueError for an unsupported model."""
    with pytest.raises(ValueError):
        get_verification_hostname("unsupported", "1234567890")


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
        ("HWE-BAT"),
    ],
)
async def test_known_products(model: str, snapshot: SnapshotAssertion):
    """Test known products."""

    product = Product.from_type(model)
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
        ("HWE-BAT"),
    ],
)
async def test_known_product_strings(model: str, snapshot: SnapshotAssertion):
    """Test generating product strings."""

    product = Product.from_type(model)
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

    product = Product.from_type(model)
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

    lhs = Product.from_type(lhs)
    rhs = Product.from_type(rhs)
    assert (lhs == rhs) == value
