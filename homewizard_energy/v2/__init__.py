"""Representation of a HomeWizard Energy device."""

from __future__ import annotations

import asyncio
import logging
import ssl
from collections.abc import Coroutine
from http import HTTPStatus
from typing import Any, Callable, TypeVar

import aiohttp
import async_timeout
import backoff

from homewizard_energy.errors import (
    DisabledError,
    NotFoundError,
    RequestError,
    ResponseError,
    UnauthorizedError,
)

from .cacert import CACERT
from .models import Device, Measurement, System, SystemUpdate
from .websocket import Websocket

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def authorized_method(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator method to check if token is set."""

    async def wrapper(self, *args, **kwargs) -> T:
        # pylint: disable=protected-access
        if self._token is None:
            raise UnauthorizedError("Token missing")

        return await func(self, *args, **kwargs)

    return wrapper


class HomeWizardEnergyV2:
    """Communicate with a HomeWizard Energy device."""

    _clientsession: aiohttp.ClientSession | None = None
    _close_clientsession: bool = False
    _request_timeout: int = 10
    _websocket: Websocket | None = None

    def __init__(
        self,
        host: str,
        identifier: str | None = None,
        token: str | None = None,
        timeout: int = 10,
    ):
        """Create a HomeWizard Energy object.

        Args:
            host: IP or URL for device.
            id: ID for device.
            token: Token for device.
            timeout: Request timeout in seconds.
        """

        self._host = host
        self._identifier = identifier
        self._token = token
        self._request_timeout = timeout

    @property
    def host(self) -> str:
        """Return the hostname of the device.

        Returns:
            host: The used host

        """
        return self._host

    @property
    def websocket(self) -> Websocket:
        """Return the websocket object.

        Create a new websocket object if it does not exist.
        """
        if self._websocket is None:
            self._websocket = Websocket(self)
        return self._websocket

    @authorized_method
    async def device(self) -> Device:
        """Return the device object."""
        _, response = await self._request("/api")
        device = Device.from_dict(response)

        return device

    @authorized_method
    async def measurement(self) -> Measurement:
        """Return the measurement object."""
        _, response = await self._request("/api/measurement")
        measurement = Measurement.from_dict(response)

        return measurement

    @authorized_method
    async def system(
        self,
        update: SystemUpdate | None = None,
    ) -> System:
        """Return the system object."""

        if update is not None:
            data = update.as_dict()
            status, response = await self._request(
                "/api/system", method=aiohttp.hdrs.METH_PUT, data=data
            )

        else:
            status, response = await self._request("/api/system")

        if status != HTTPStatus.OK:
            error = response.get("errodr", response)
            raise RequestError(f"Failed to get system: {error}")

        system = System.from_dict(response)
        return system

    @authorized_method
    async def identify(
        self,
    ) -> bool:
        """Send identify request."""
        await self._request("/api/system/identify", method=aiohttp.hdrs.METH_PUT)
        return True

    async def get_token(
        self,
        name: str,
    ) -> str:
        """Get authorization token from device."""
        status, response = await self._request(
            "/api/user", method=aiohttp.hdrs.METH_POST, data={"name": f"local/{name}"}
        )

        if status == HTTPStatus.FORBIDDEN:
            raise DisabledError("User creation is not enabled on the device")

        if status != HTTPStatus.OK:
            error = response.get("error", response)
            raise RequestError(f"Error occurred while getting token: {error}")

        try:
            token = response["token"]
        except KeyError as ex:
            raise ResponseError("Failed to get token") from ex

        self._token = token
        return token

    @authorized_method
    async def delete_token(
        self,
        name: str | None = None,
    ) -> None:
        """Delete authorization token from device."""
        status, response = await self._request(
            "/api/user",
            method=aiohttp.hdrs.METH_DELETE,
            data={"name": name} if name is not None else None,
        )

        if status != HTTPStatus.NO_CONTENT:
            error = response.get("error", response)
            raise RequestError(f"Error occurred while getting token: {error}")

        # Our token was invalided, resetting it
        if name is None:
            self._token = None

    @property
    def token(self) -> str | None:
        """Return the token of the device.

        Returns:
            token: The used token

        """
        return self._token

    @property
    def request_timeout(self) -> int:
        """Return the request timeout of the device.

        Returns:
            request_timeout: The used request timeout

        """
        return self._request_timeout

    async def get_clientsession(self) -> aiohttp.ClientSession:
        """
        Get a clientsession that is tuned for communication with the HomeWizard Energy Device
        """

        if self._clientsession is not None:
            return self._clientsession

        def _build_ssl_context() -> ssl.SSLContext:
            context = ssl.create_default_context(cadata=CACERT)
            if self._identifier is not None:
                context.hostname_checks_common_name = True
            else:
                _LOGGER.warning("No hostname provided, skipping hostname validation")
                context.check_hostname = False  # Skip hostname validation
                context.verify_mode = ssl.CERT_REQUIRED  # Keep SSL verification active
            return context

        # Creating an SSL context has some blocking IO so need to run it in the executor
        loop = asyncio.get_running_loop()
        context = await loop.run_in_executor(None, _build_ssl_context)

        connector = aiohttp.TCPConnector(
            enable_cleanup_closed=True,
            ssl=context,
            limit_per_host=1,
        )

        self._clientsession = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self._request_timeout),
        )

        return self._clientsession

    @backoff.on_exception(backoff.expo, RequestError, max_tries=5, logger=None)
    async def _request(
        self, path: str, method: str = aiohttp.hdrs.METH_GET, data: object = None
    ) -> Any:
        """Make a request to the API."""

        _clientsession = await self.get_clientsession()

        if _clientsession.closed:
            # Avoid runtime errors when connection is closed.
            # This solves an issue when updates were scheduled and clientsession was closed.
            return None

        # Construct request
        url = f"https://{self.host}{path}"
        headers = {
            "Content-Type": "application/json",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        _LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(self._request_timeout):
                resp = await _clientsession.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    server_hostname=self._identifier
                    if self._identifier is not None
                    else None,
                )
                _LOGGER.debug("%s, %s", resp.status, await resp.text("utf-8"))
        except asyncio.TimeoutError as exception:
            raise RequestError(
                f"Timeout occurred while connecting to the HomeWizard Energy device at {self.host}"
            ) from exception
        except (aiohttp.ClientError, aiohttp.ClientResponseError) as exception:
            raise RequestError(
                f"Error occurred while communicating with the HomeWizard Energy device at {self.host}"
            ) from exception

        match resp.status:
            case HTTPStatus.UNAUTHORIZED:
                raise UnauthorizedError("Token rejected")
            case HTTPStatus.METHOD_NOT_ALLOWED:
                raise NotFoundError("Method not allowed")
            case HTTPStatus.NO_CONTENT:
                # No content, just return
                return (HTTPStatus.NO_CONTENT, None)
            case HTTPStatus.OK:
                pass

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return (resp.status, await resp.json())

        return (resp.status, await resp.text())

    async def close(self) -> None:
        """Close client session."""
        _LOGGER.debug("Closing clientsession")
        if self._clientsession is not None:
            await self._clientsession.close()
            self._clientsession = None

    async def __aenter__(self) -> HomeWizardEnergyV2:
        """Async enter.

        Returns:
            The HomeWizardEnergyV2 object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
