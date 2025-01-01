"""Test the helper functions."""

import pytest

from homewizard_energy.models import get_verification_hostname

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
