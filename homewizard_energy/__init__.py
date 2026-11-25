"""HomeWizard Energy API library."""

import asyncio
from contextlib import suppress
from typing import Any

from aiohttp import ClientSession

from .const import MODEL_TO_ID, SUPPORTED_V2_MODELS
from .errors import DisabledError, InvalidStateError, RequestError, UnsupportedError
from .homewizard_energy import HomeWizardEnergy
from .v1 import HomeWizardEnergyV1
from .v2 import HomeWizardEnergyV2, create_ssl_context

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

# Some devices have a certificate without product type, e.g. early batteries
# with `appliance/generic/<serial>`
GENERIC_CERTIFICATE_ID = "generic"

# Timeout in seconds for connecting to the device and for its response
TIMEOUT = 5


def _get_certificate_product_id(certificate: dict[str, Any] | None) -> str | None:
    """Get the product type identifier from a device certificate.

    The common name of the certificate is formatted as
    `appliance/<product type identifier>/<serial>`, see `MODEL_TO_ID`.
    """
    for rdn in (certificate or {}).get("subject", ()):
        for key, value in rdn:
            if key != "commonName":
                continue
            parts = value.split("/")
            if len(parts) == 3 and parts[0] == "appliance":
                return parts[1]

    return None


async def _get_v2_product_id(host: str) -> str | None:
    """Get the product type identifier of a device that serves the v2 API.

    Only devices with the v2 API serve HTTPS with a valid device certificate,
    which contains the product type identifier. Some firmware serves this
    certificate without the v2 API, so also check that the API responds to a
    request without a token with 401 Unauthorized.

    This works without authorization, and needs only a single connection,
    as devices have very few connection slots.
    """
    loop = asyncio.get_running_loop()
    # Creating an SSL context has some blocking IO so need to run it in the executor
    context = await loop.run_in_executor(None, create_ssl_context, False)

    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, 443, ssl=context), timeout=TIMEOUT
    )
    try:
        product_id = _get_certificate_product_id(writer.get_extra_info("peercert"))
        if product_id is None:
            return None

        host_header = f"[{host}]" if ":" in host else host
        request = (
            f"GET /api HTTP/1.1\r\nHost: {host_header}\r\nConnection: close\r\n\r\n"
        )
        writer.write(request.encode())
        await writer.drain()
        status_line = await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)
    finally:
        writer.close()
        # Closing raises an SSL error when the rest of the response is not read yet
        with suppress(OSError):
            await asyncio.wait_for(writer.wait_closed(), timeout=TIMEOUT)

    # Status line is formatted as `HTTP/1.1 401 Unauthorized`
    parts = status_line.split()
    if len(parts) < 2 or parts[1] != b"401":
        return None

    return product_id


async def has_v2_api(
    host: str,
    websession: ClientSession | None = None,
    product_type: str | None = None,
) -> bool:
    """Check if the device has support for the v2 api.

    Only returns True for models that are supported via the v2 API by this
    version of the library (see `SUPPORTED_V2_MODELS`), so devices that enable
    the v2 API before it is officially supported keep using the v1 API.

    The product type is read from the device certificate, and the device must
    respond to a request without a token with 401 Unauthorized. Pass `product_type`
    when it is already known (e.g. from discovery or an existing configuration):
    unsupported models then return False without connecting to the device, and
    a device of another product type at this host returns False as well.
    Some devices have a generic certificate without product type; those are
    reported as v2 capable when they serve the v2 API and `product_type`, when
    passed, is supported.

    `websession` is no longer used and only kept for backwards compatibility.
    """
    del websession  # Kept for backwards compatibility

    if product_type is not None and product_type not in SUPPORTED_V2_MODELS:
        return False

    try:
        product_id = await _get_v2_product_id(host)
    except OSError:
        # Includes SSL errors and timeouts. No (valid) HTTPS connection means
        # the device is not v2 or not reachable at this time
        return False

    if product_id == GENERIC_CERTIFICATE_ID:
        # The certificate doesn't tell the product type, so rely on the
        # `product_type` that passed the check above, or on the API response
        return True

    if product_type is not None:
        return product_id == MODEL_TO_ID[product_type]

    return product_id in SUPPORTED_V2_CERTIFICATE_IDS
