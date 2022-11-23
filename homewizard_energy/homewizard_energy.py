"""Representation of a HomeWizard Energy device."""
from __future__ import annotations

import asyncio
import logging

import async_timeout
from aiohttp.client import ClientError, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_GET, METH_PUT

from .const import SUPPORTED_API_VERSION
from .errors import DisabledError, RequestError, UnsupportedError
from .features import Features
from .models import Data, Device, State, System

_LOGGER = logging.getLogger(__name__)


class HomeWizardEnergy:
    """Communicate with a HomeWizard Energy device."""

    _session: ClientSession | None
    _close_session: bool = False
    _request_timeout: int = 10

    _features: Features | None = None

    def __init__(
        self, host: str, clientsession: ClientSession = None, timeout: int = 10
    ):
        """Create a HomeWizard Energy object.

        Args:
            host: IP or URL for device.
            clientsession: The clientsession.
        """

        self._host = host
        self._session = clientsession
        self._request_timeout = timeout

    @property
    def host(self) -> str:
        """Return the hostname of the device.

        Returns:
            host: The used host

        """
        return self._host

    async def features(self) -> Features:
        """Create or return Features object."""
        if self.features is None:
            await self.device()

        return self._features

    async def device(self) -> Device:
        """Return the device object."""
        response = await self.request("api")
        device = Device.from_dict(response)

        self._features = Features(device.product_type, device.firmware_version)

        if device.api_version != SUPPORTED_API_VERSION:
            raise UnsupportedError(
                f"Unsupported API version, expected version '{SUPPORTED_API_VERSION}'"
            )

        return device

    async def data(self) -> Data:
        """Return the data object."""
        response = await self.request("api/v1/data")
        return Data.from_dict(response)

    async def state(self) -> State | None:
        """Return the state object."""
        features = await self.features()
        if not features.has_state:
            return None

        response = await self.request("api/v1/state")
        return State.from_dict(response)

    async def state_set(
        self,
        power_on: bool | None = None,
        switch_lock: bool | None = None,
        brightness: int | None = None,
    ) -> bool:
        """Set state of device."""
        state = {}
        features = await self.features()
        if not features.has_state:
            raise UnsupportedError("Setting state is not supported with this device")

        if power_on is not None:
            state["power_on"] = power_on
        if switch_lock is not None:
            state["switch_lock"] = switch_lock
        if brightness is not None:
            state["brightness"] = brightness

        if not state:
            _LOGGER.error("At least one state update is required")
            return False

        await self.request("api/v1/state", method=METH_PUT, data=state)
        return True

    async def system(self) -> System:
        """Return the system object."""
        response = await self.request("api/v1/system")
        return System.from_dict(response)

    async def system_set(
        self,
        cloud_enabled: bool | None = None,
    ) -> bool:
        """Set state of device."""
        state = {}
        features = await self.features()
        if not features.has_system:
            raise UnsupportedError("Setting system is not supported with this device")

        if cloud_enabled is not None:
            state["cloud_enabled"] = cloud_enabled

        if not state:
            _LOGGER.error("At least one state update is required")
            return False

        await self.request("api/v1/system", method=METH_PUT, data=state)
        return True

    async def identify(
        self,
    ) -> bool:
        """Send identify request."""
        features = await self.features()
        if not features.has_identify:
            raise UnsupportedError("Identify is not supported")

        await self.request("api/v1/identify", method=METH_PUT)
        return True

    async def request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> object | None:
        """Make a request to the API."""
        if self._session is None:
            self._session = ClientSession()
            self._close_session = True

        url = f"http://{self.host}/{path}"
        headers = {"Content-Type": "application/json"}

        _LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(self._request_timeout):
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
        if "application/json" in content_type:
            return await resp.json()

        return await resp.text()

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
