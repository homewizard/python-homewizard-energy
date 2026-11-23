"""HomeWizard Energy API library."""

import asyncio
import ssl
from functools import cache

from aiohttp import ClientSession

from .const import MODEL_TO_ID, SUPPORTED_V2_MODELS
from .errors import DisabledError, InvalidStateError, RequestError, UnsupportedError
from .homewizard_energy import HomeWizardEnergy
from .v1 import HomeWizardEnergyV1
from .v2 import HomeWizardEnergyV2
from .v2.cacert import CACERT

__all__ = [
    "DisabledError",
    "HomeWizardEnergy",
    "HomeWizardEnergyV1",
    "HomeWizardEnergyV2",
    "InvalidStateError",
    "RequestError",
    "UnsupportedError",
]

# Product type identifiers as used in the device certificate,
# for the models that are supported via the v2 API
SUPPORTED_V2_CERTIFICATE_IDS = frozenset(
    MODEL_TO_ID[model] for model in SUPPORTED_V2_MODELS
)


@cache
def _certificate_ssl_context() -> ssl.SSLContext:
    """SSL context that validates the device certificate, but not the hostname."""
    context = ssl.create_default_context(cadata=CACERT)
    context.verify_flags = ssl.VERIFY_X509_PARTIAL_CHAIN  # pylint: disable=no-member
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    return context


async def _get_certificate_product_id(host: str) -> str | None:
    """Get the product type identifier from the device certificate.

    The common name of the certificate of a v2 device is formatted as
    `appliance/<product type identifier>/<serial>`, see `MODEL_TO_ID`.
    This works without authorization.
    """
    loop = asyncio.get_running_loop()
    # Loading the CA certificate is blocking IO, so run it in the executor
    context = await loop.run_in_executor(None, _certificate_ssl_context)

    _, writer = await asyncio.wait_for(
        asyncio.open_connection(host, 443, ssl=context), timeout=5
    )
    try:
        certificate = writer.get_extra_info("peercert") or {}
    finally:
        writer.close()

    for rdn in certificate.get("subject", ()):
        for key, value in rdn:
            if key != "commonName":
                continue
            parts = value.split("/")
            if len(parts) == 3 and parts[0] == "appliance":
                return parts[1]

    return None


async def has_v2_api(host: str, websession: ClientSession | None = None) -> bool:
    """Check if the device has support for the v2 api.

    Only returns True for models that are supported via the v2 API by this
    version of the library (see `SUPPORTED_V2_MODELS`), so devices that enable
    the v2 API before it is officially supported keep using the v1 API.
    """
    websession_provided = websession is not None
    if websession is None:
        websession = ClientSession()
    try:
        # v2 api is https only and returns a 401 Unauthorized when no key provided,
        # no connection can be made if the device is not v2
        url = f"https://{host}/api"
        res = await websession.get(url, ssl=False, raise_for_status=False, timeout=5)
        res.close()

        if res.status != 401:
            return False

        # The unauthorized response does not tell which product this is,
        # so get the product type from the device certificate instead
        return await _get_certificate_product_id(host) in SUPPORTED_V2_CERTIFICATE_IDS
    except Exception:  # pylint: disable=broad-except
        # all other status/exceptions means the device is not v2 or not reachable at this time
        return False
    finally:
        if not websession_provided:
            await websession.close()
