"""Representation of a HomeWizard Energy device."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from http import HTTPStatus
from typing import Any, TypeVar

import async_timeout
import backoff
from aiohttp.client import ClientError, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_GET, METH_PUT

from homewizard_energy.errors import (
    DisabledError,
    NotFoundError,
    RequestError,
    UnsupportedError,
)

from ..models import Device
from .const import SUPPORTED_API_VERSION
from .models import Data, State, System

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def optional_method(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """Check if method is supported."""

    async def wrapper(self, *args, **kwargs) -> T:
        try:
            return await func(self, *args, **kwargs)
        except NotFoundError as ex:
            raise UnsupportedError(f"{func.__name__} is not supported") from ex

    return wrapper


class HomeWizardEnergyV1:
    """Communicate with a HomeWizard Energy device."""

    _session: ClientSession | None
    _close_session: bool = False
    _request_timeout: int = 10

    def __init__(
        self, host: str, clientsession: ClientSession = None, timeout: int = 10
    ):
        """Create a HomeWizard Energy object.

        Args:
            host: IP or URL for device.
            clientsession: The clientsession.
            timeout: Request timeout in seconds.
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

    async def device(self) -> Device:
        """Return the device object."""
        response = await self.request("api")
        device = Device.from_dict(response)

        if device.api_version != SUPPORTED_API_VERSION:
            raise UnsupportedError(
                f"Unsupported API version, expected version '{SUPPORTED_API_VERSION}'"
            )

        return device

    async def data(self) -> Data:
        """Return the data object."""
        response = await self.request("api/v1/data")
        return Data.from_dict(response)

    @optional_method
    async def state(self) -> State | None:
        """Return the state object."""
        response = await self.request("api/v1/state")
        return State.from_dict(response)

    @optional_method
    async def state_set(
        self,
        power_on: bool | None = None,
        switch_lock: bool | None = None,
        brightness: int | None = None,
    ) -> bool:
        """Set state of device."""
        state: dict[str, bool | str] = {}

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

    @optional_method
    async def system(self) -> System:
        """Return the system object."""
        response = await self.request("api/v1/system")
        return System.from_dict(response)

    @optional_method
    async def system_set(
        self,
        cloud_enabled: bool | None = None,
    ) -> bool:
        """Set state of device."""
        state = {}
        if cloud_enabled is not None:
            state["cloud_enabled"] = cloud_enabled

        if not state:
            _LOGGER.error("At least one state update is required")
            return False

        await self.request("api/v1/system", method=METH_PUT, data=state)
        return True

    @optional_method
    async def identify(
        self,
    ) -> bool:
        """Send identify request."""
        await self.request("api/v1/identify", method=METH_PUT)
        return True

    @backoff.on_exception(backoff.expo, RequestError, max_tries=5, logger=None)
    async def request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> Any:
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
                f"Timeout occurred while connecting to the HomeWizard Energy device at {self.host}"
            ) from exception
        except (ClientError, ClientResponseError) as exception:
            raise RequestError(
                f"Error occurred while communicating with the HomeWizard Energy device at {self.host}"
            ) from exception

        if resp.status == HTTPStatus.FORBIDDEN:
            # Known case: API disabled
            raise DisabledError(
                "API disabled. API must be enabled in HomeWizard Energy app"
            )

        if resp.status == HTTPStatus.NOT_FOUND:
            # Known case: API endpoint not supported
            raise NotFoundError("Resource not found")

        if resp.status != HTTPStatus.OK:
            # Something else went wrong
            raise RequestError(f"API request error ({resp.status})")

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await resp.json()

        return await resp.text()

    async def close(self) -> None:
        """Close client session."""
        _LOGGER.debug("Closing clientsession")
        if self._session and self._close_session:
            await self._session.close()

    async def __aenter__(self) -> HomeWizardEnergyV1:
        """Async enter.

        Returns:
            The HomeWizardEnergyV1 object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
