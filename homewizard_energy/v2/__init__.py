"""Representation of a HomeWizard Energy device."""

from __future__ import annotations

import asyncio
import json
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
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_POST, METH_PUT
from mashumaro.exceptions import InvalidFieldValue, MissingField

from homewizard_energy.errors import (
    DisabledError,
    RequestError,
    ResponseError,
    UnauthorizedError,
)

from ..const import LOGGER
from ..homewizard_energy import HomeWizardEnergy
from ..models import Device, Measurement, System, SystemUpdate, Token
from .cacert import CACERT

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


# pylint: disable=abstract-method
class HomeWizardEnergyV2(HomeWizardEnergy):
    """Communicate with a HomeWizard Energy device."""

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        host: str,
        identifier: str | None = None,
        token: str | None = None,
        clientsession: ClientSession = None,
        timeout: int = 10,
    ):
        """Create a HomeWizard Energy object.

        Args:
            host: IP or URL for device.
            id: ID for device.
            token: Token for device.
            timeout: Request timeout in seconds.
        """
        super().__init__(host, clientsession, timeout)
        self._identifier = identifier
        self._token = token

    @authorized_method
    async def device(self) -> Device:
        """Return the device object."""
        _, response = await self._request("/api")
        device = Device.from_json(response)

        return device

    @authorized_method
    async def measurement(self) -> Measurement:
        """Return the measurement object."""
        _, response = await self._request("/api/measurement")
        measurement = Measurement.from_json(response)

        return measurement

    @authorized_method
    async def system(
        self,
        update: SystemUpdate | None = None,
    ) -> System:
        """Return the system object."""

        if update is not None:
            data = update.to_dict()
            status, response = await self._request(
                "/api/system", method=METH_PUT, data=data
            )

        else:
            status, response = await self._request("/api/system")

        if status != HTTPStatus.OK:
            error = json.loads(response).get("error", response)
            raise RequestError(f"Failed to get system: {error}")

        system = System.from_json(response)
        return system

    @authorized_method
    async def identify(
        self,
    ) -> None:
        """Send identify request."""
        await self._request("/api/system/identify", method=METH_PUT)

    @authorized_method
    async def reboot(
        self,
    ) -> None:
        """Reboot the HomeWizard Energy device.

        This will cause the device to restart, resulting in temporary unavailability.
        The reboot process typically takes a few seconds to complete.

        Note: A reboot is usually not necessary.
        Make sure to inform the user that if the issue persists and frequent reboots are required,
        they need to contact our support team to help identify and resolve the root cause.
        """
        await self._request("/api/system/reboot", method=METH_PUT)

    async def get_token(
        self,
        name: str,
    ) -> str:
        """Get authorization token from device."""
        status, response = await self._request(
            "/api/user", method=METH_POST, data={"name": f"local/{name}"}
        )

        if status == HTTPStatus.FORBIDDEN:
            raise DisabledError("User creation is not enabled on the device")

        if status != HTTPStatus.OK:
            error = json.loads(response).get("error", response)
            raise RequestError(f"Error occurred while getting token: {error}", error)

        try:
            token = Token.from_json(response).token
        except (InvalidFieldValue, MissingField) as ex:
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
            method=METH_DELETE,
            data={"name": name} if name is not None else None,
        )

        if status != HTTPStatus.NO_CONTENT:
            error = json.loads(response).get("error", response)
            raise RequestError(f"Error occurred while getting token: {error}", error)

        # Our token was invalided, resetting it
        if name is None:
            self._token = None

    async def _get_session(self) -> ClientSession:
        """
        Get a clientsession that is tuned for communication with the HomeWizard Energy Device
        """

        def _build_ssl_context() -> ssl.SSLContext:
            context = ssl.create_default_context(cadata=CACERT)
            if self._identifier is not None:
                context.hostname_checks_common_name = True
            else:
                LOGGER.warning("No hostname provided, skipping hostname validation")
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
    async def _request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> tuple[HTTPStatus, dict[str, Any] | None]:
        """Make a request to the API."""

        if self._session is None:
            self._session = await self._get_session()

        # Construct request
        url = f"https://{self.host}{path}"
        headers = {
            "Content-Type": "application/json",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(self._request_timeout):
                resp = await self._session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    server_hostname=self._identifier
                    if self._identifier is not None
                    else None,
                )
                LOGGER.debug("%s, %s", resp.status, await resp.text("utf-8"))
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
            case HTTPStatus.NO_CONTENT:
                # No content, just return
                return (HTTPStatus.NO_CONTENT, None)
            case HTTPStatus.OK:
                pass

        return (resp.status, await resp.text())
