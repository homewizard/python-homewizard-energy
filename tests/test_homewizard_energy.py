"""Test the base class."""

import pytest

from homewizard_energy.errors import UnsupportedError
from homewizard_energy.homewizard_energy import HomeWizardEnergy

pytestmark = [pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("function", "exception"),
    [
        ("device", NotImplementedError),
        ("measurement", NotImplementedError),
        ("system", NotImplementedError),
        ("state", UnsupportedError),
        ("identify", NotImplementedError),
        ("reboot", UnsupportedError),
    ],
)
async def test_base_class_raises_notimplementederror(
    function: str, exception: Exception
):
    """Test the base class raises NotImplementedError."""
    with pytest.raises(exception):
        async with HomeWizardEnergy("host") as api:
            await getattr(api, function)()
