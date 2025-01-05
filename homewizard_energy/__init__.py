"""HomeWizard Energy API library."""

from aiohttp import ClientSession

from .errors import DisabledError, InvalidStateError, RequestError, UnsupportedError
from .homewizard_energy import HomeWizardEnergy
from .v1 import HomeWizardEnergyV1
from .v2 import HomeWizardEnergyV2

__all__ = [
    "DisabledError",
    "HomeWizardEnergy",
    "HomeWizardEnergyV1",
    "HomeWizardEnergyV2",
    "InvalidStateError",
    "RequestError",
    "UnsupportedError",
]


async def has_v2_api(host: str, websession: ClientSession | None = None) -> bool:
    """Check if the device has support for the v2 api."""
    websession_provided = websession is not None
    if websession is None:
        websession = ClientSession()
    try:
        # v2 api is https only and returns a 401 Unauthorized when no key provided,
        # no connection can be made if the device is not v2
        url = f"https://{host}/api"
        res = await websession.get(url, ssl=False, raise_for_status=False, timeout=5)
        res.close()

        return res.status == 401
    except Exception:  # pylint: disable=broad-except
        # all other status/exceptions means the device is not v2 or not reachable at this time
        return False
    finally:
        if not websession_provided:
            await websession.close()
