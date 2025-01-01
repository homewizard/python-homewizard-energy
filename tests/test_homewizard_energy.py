"""Test the base class."""

import pytest

from homewizard_energy.homewizard_energy import HomeWizardEnergy

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("function"),
    [
        ("device"),
        ("measurement"),
        ("system"),
        ("state"),
        ("identify"),
        ("reboot"),
    ],
)
async def test_base_class_raises_notimplementederror(function: str):
    """Test the base class raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        async with HomeWizardEnergy("host") as api:
            await getattr(api, function)()
