"""Representation of a HomeWizard Energy device."""

from __future__ import annotations

import asyncio
import logging
import ssl
from collections.abc import Callable, Coroutine
from http import HTTPStatus
from typing import Any, TypeVar

import async_timeout
import backoff
from aiohttp.client import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    TCPConnector,
)
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT

from homewizard_energy.errors import (
    DisabledError,
    NotFoundError,
    RequestError,
    UnauthorizedError,
)

from .cacert import CACERT
from .models import Device

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

    _clientsession: ClientSession | None = None
    _close_clientsession: bool = False
    _request_timeout: int = 10

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

    @authorized_method
    async def device(self) -> Device:
        """Return the device object."""
        response = await self.request("api")
        device = Device.from_dict(response)

        return device

    @authorized_method
    async def identify(
        self,
    ) -> bool:
        """Send identify request."""
        await self.request("api/v2/system/identify", method=METH_PUT)
        return True

    async def get_user_token(
        self,
        name: str | None = None,
    ) -> str:
        """Get authorization token from device."""
        response = await self.request(
            "api/v2/user", method=METH_POST, data={"name": name}
        )

        if error := response.get("error"):
            # Specific case, expecting button press
            if error == "user:creation-not-enabled":
                raise DisabledError("User creation is not enabled on the device")

            raise RequestError(f"Error occurred while getting token: {error}")

        token = response.get("user").get("token")
        if token is None:
            raise RequestError("Failed to get token")

        self._token = token
        return token

    async def _get_clientsession(self) -> ClientSession:
        """
        Get a clientsession that is tuned for communication with the HomeWizard Energy Device
        """

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

        connector = TCPConnector(
            enable_cleanup_closed=True,
            ssl=context,
            limit_per_host=1,
        )

        return ClientSession(
            connector=connector, timeout=ClientTimeout(total=self._request_timeout)
        )

    @backoff.on_exception(backoff.expo, RequestError, max_tries=5, logger=None)
    async def request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> Any:
        """Make a request to the API."""

        if self._clientsession is None:
            self._clientsession = await self._get_clientsession()

        if self._clientsession.closed:
            # Avoid runtime errors when connection is closed.
            # This solves an issue when updates were scheduled and clientsession was closed.
            return None

        # Construct request
        url = f"https://{self.host}/{path}"
        headers = {
            "Content-Type": "application/json",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        _LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(self._request_timeout):
                resp = await self._clientsession.request(
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
        except (ClientError, ClientResponseError) as exception:
            raise RequestError(
                f"Error occurred while communicating with the HomeWizard Energy device at {self.host}"
            ) from exception

        match resp.status:
            case HTTPStatus.UNAUTHORIZED:
                raise UnauthorizedError("Token rejected")
            case HTTPStatus.NOT_FOUND:
                raise NotFoundError("Resource not found")
            case HTTPStatus.NO_CONTENT:
                # No content, just return
                return None

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await resp.json()

        return await resp.text()

    async def close(self) -> None:
        """Close client session."""
        _LOGGER.debug("Closing clientsession")
        if self._clientsession is not None:
            await self._clientsession.close()

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
