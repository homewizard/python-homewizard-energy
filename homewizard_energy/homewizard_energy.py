"""Representation of a HomeWizard Energy device."""
from __future__ import annotations

import asyncio
import logging

import async_timeout
from aiohttp.client import ClientError, ClientResponseError, ClientSession

from .const import DEVICES_WITH_STATE, SUPPORTED_API_VERSION
from .errors import DisabledError, RequestError, UnsupportedError
from .models import Data, Device, State

_LOGGER = logging.getLogger(__name__)


class HomeWizardEnergy:
    """Communicate with a HomeWizard Energy device."""

    _session: ClientSession | None
    _close_session: bool = False

    _detected_product_type: str | None = None
    _detected_api_version: str | None = None

    def __init__(self, host: str, clientsession: ClientSession = None):
        """Create a HomeWizard Energy object.

        Args:
            host: IP or URL for device.
            clientsession: The clientsession.
        """

        self._host = host
        self._session = clientsession

    @property
    def host(self) -> str:
        """Return the hostname of the device.

        Returns:
            host: The used host

        """
        return self._host

    async def device(self) -> Device:
        """Return the device object."""
        response = await self.request("api")
        device = Device.from_dict(response)

        self._detected_product_type = device.product_type
        self._detected_api_version = device.api_version

        if device.api_version != SUPPORTED_API_VERSION:
            raise UnsupportedError(
                f"Unsupported API version, expected version '{SUPPORTED_API_VERSION}'"
            )

        return device

    async def data(self) -> Data:
        """Return the data object."""
        if not self._detected_api_version:
            await self.device()

        if self._detected_api_version != SUPPORTED_API_VERSION:
            raise UnsupportedError(
                f"Unsupported API version, detected {self._detected_api_version}"
            )

        response = await self.request("api/v1/data")
        return Device.from_dict(response)

    async def state(self) -> State | None:
        """Return the state object."""
        if not self._detected_api_version or not self._detected_product_type:
            await self.device()

        if self._detected_product_type not in DEVICES_WITH_STATE:
            return None

        if self._detected_api_version != SUPPORTED_API_VERSION:
            raise UnsupportedError(
                f"Unsupported device or API version, "
                f"detected API:{self._detected_api_version} with {self._detected_product_type}"
            )

        response = await self.request("api/v1/state")
        return State.from_dict(response)

    async def request(
        self, path: str, method: str = "get", data: object = None
    ) -> object | None:
        """Make a request to the API."""
        if self._session is None:
            self._session = ClientSession()
            self._close_session = True

        url = f"http://{self.host}/{path}"
        headers = {"Content-Type": "application/json"}

        _LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(8):
                resp = await self._session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                )
                _LOGGER.debug("%s, %s", resp.status, await resp.text("utf-8"))
        except asyncio.TimeoutError as exception:
            raise RequestError(
                "Timeout occurred while connecting to the HomeWizard Energy device"
            ) from exception
        except (ClientError, ClientResponseError) as exception:
            raise RequestError(
                "Error occurred while communicating with the HomeWizard Energy device"
            ) from exception

        if resp.status == 403:
            # Known case: API disabled
            raise DisabledError(
                "API disabled. API must be enabled in HomeWizard Energy app"
            )

        if resp.status != 200:
            # Something else went wrong
            raise RequestError(f"API request error ({resp.status})")

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise RequestError("Unexpected content type")

        return await resp.json()

    async def close(self):
        """Close client session."""
        _LOGGER.debug("Closing clientsession")
        if self._session and self._close_session:
            await self._session.close()

    async def __aenter__(self) -> HomeWizardEnergy:
        """Async enter.

        Returns:
            The HomeWizardEnergy object.
        """
        return self

    async def __aexit__(self, *_exc_info) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
