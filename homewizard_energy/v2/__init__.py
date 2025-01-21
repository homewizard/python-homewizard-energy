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
from aiohttp.client import ClientError, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_POST, METH_PUT
from mashumaro.exceptions import InvalidFieldValue, MissingField

from ..const import LOGGER
from ..errors import (
    DisabledError,
    InvalidUserNameError,
    RequestError,
    ResponseError,
    UnauthorizedError,
)
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

    _ssl: ssl.SSLContext | bool = False
    _identifier: str | None = None

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
    async def device(self, reset_cache: bool = False) -> Device:
        """Return the device object."""
        if self._device is not None and not reset_cache:
            return self._device

        _, response = await self._request("/api")
        device = Device.from_json(response)

        # Cache device object
        self._device = device
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
        cloud_enabled: bool | None = None,
        status_led_brightness_pct: int | None = None,
        api_v1_enabled: bool | None = None,
    ) -> System:
        """Return the system object."""

        if (
            cloud_enabled is not None
            or status_led_brightness_pct is not None
            or api_v1_enabled is not None
        ):
            data = SystemUpdate(
                cloud_enabled=cloud_enabled,
                status_led_brightness_pct=status_led_brightness_pct,
                api_v1_enabled=api_v1_enabled,
            ).to_dict()
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
            raise InvalidUserNameError(
                f"Error occurred while getting token: {error}", error
            )

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

    async def _get_ssl_context(self) -> ssl.SSLContext:
        """
        Get a clientsession that is tuned for communication with the HomeWizard Energy Device
        """

        def _build_ssl_context() -> ssl.SSLContext:
            context = ssl.create_default_context(cadata=CACERT)
            context.verify_flags = ssl.VERIFY_X509_PARTIAL_CHAIN  # pylint: disable=no-member
            if self._identifier is not None:
                context.hostname_checks_common_name = True
            else:
                LOGGER.warning("No hostname provided, skipping hostname validation")
                context.check_hostname = False  # Skip hostname validation
                context.verify_mode = ssl.CERT_REQUIRED  # Keep SSL verification active
            return context

        # Creating an SSL context has some blocking IO so need to run it in the executor
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _build_ssl_context)

    @backoff.on_exception(backoff.expo, RequestError, max_tries=3, logger=None)
    async def _request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> tuple[HTTPStatus, dict[str, Any] | None]:
        """Make a request to the API."""

        if self._session is None:
            await self._create_clientsession()

        if self._ssl is False:
            self._ssl = await self._get_ssl_context()

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
                    ssl=self._ssl,
                    server_hostname=self._identifier,
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

    async def __aenter__(self) -> HomeWizardEnergyV2:
        """Async enter.

        Returns:
            The HomeWizardEnergyV2 object.
        """
        return self
