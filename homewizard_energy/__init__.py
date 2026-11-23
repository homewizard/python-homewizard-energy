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

    Only devices with the v2 API serve HTTPS. The common name of their
    certificate is formatted as `appliance/<product type identifier>/<serial>`,
    see `MODEL_TO_ID`. This works without authorization, and only needs a single
    TLS handshake, as devices have very few connection slots.
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


async def has_v2_api(
    host: str,
    websession: ClientSession | None = None,
    product_type: str | None = None,
) -> bool:
    """Check if the device has support for the v2 api.

    Only returns True for models that are supported via the v2 API by this
    version of the library (see `SUPPORTED_V2_MODELS`), so devices that enable
    the v2 API before it is officially supported keep using the v1 API.

    The product type is read from the device certificate. Pass `product_type`
    when it is already known (e.g. from discovery or an existing configuration):
    unsupported models then return False without connecting to the device, and
    a device of another product type at this host returns False as well.

    `websession` is no longer used and only kept for backwards compatibility.
    """
    del websession  # Kept for backwards compatibility

    if product_type is not None and product_type not in SUPPORTED_V2_MODELS:
        return False

    try:
        product_id = await _get_certificate_product_id(host)
    except Exception:  # pylint: disable=broad-except
        # No (valid) HTTPS connection means the device is not v2
        # or not reachable at this time
        return False

    if product_type is not None:
        return product_id == MODEL_TO_ID[product_type]

    return product_id in SUPPORTED_V2_CERTIFICATE_IDS
