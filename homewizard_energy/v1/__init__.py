"""Representation of a HomeWizard Energy device."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from http import HTTPStatus
from typing import Any, TypeVar

import async_timeout
import backoff
from aiohttp.client import ClientError, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_GET, METH_PUT

from ..const import LOGGER
from ..errors import DisabledError, NotFoundError, RequestError, UnsupportedError
from ..homewizard_energy import HomeWizardEnergy
from ..models import (
    CombinedModels,
    Device,
    Measurement,
    State,
    StateUpdate,
    System,
    SystemUpdate,
)

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


# pylint: disable=abstract-method
class HomeWizardEnergyV1(HomeWizardEnergy):
    """Communicate with a HomeWizard Energy device."""

    async def combined(self) -> CombinedModels:
        """Get all information."""

        models: CombinedModels = await super().combined()

        # Move things around for backwards compatibility
        ## measurement.wifi_ssid -> system.wifi_ssid
        if models.measurement is not None and models.measurement.wifi_ssid is not None:
            if models.system is None:
                models.system = System()
            models.system.wifi_ssid = models.measurement.wifi_ssid

        ## state.brightness -> system.status_led_brightness_pct
        if models.state is not None and models.state.brightness is not None:
            if models.system is None:
                models.system = System()
            models.system.status_led_brightness_pct = (
                models.state.brightness / 255
            ) * 100

        return models

    async def device(self) -> Device:
        """Return the device object."""
        _, response = await self._request("api")
        device = Device.from_json(response)

        return device

    async def measurement(self) -> Measurement:
        """Return the data object."""
        _, response = await self._request("api/v1/data")
        return Measurement.from_json(response)

    @optional_method
    async def state(self, update: StateUpdate | None = None) -> State:
        """Return or update the state object."""

        if self._device is not None and self._device.supports_state is False:
            raise UnsupportedError("State is not supported")

        if update is not None:
            data = update.to_dict()
            status, response = await self._request(
                "api/v1/state", method=METH_PUT, data=data
            )

        else:
            status, response = await self._request("api/v1/state")

        if status != HTTPStatus.OK:
            raise RequestError("Failed to get/set state")

        state = State.from_json(response)
        return state

    @optional_method
    async def system(self, update: SystemUpdate | None = None) -> System:
        """Return the system object."""
        if update is not None:
            if (
                update.status_led_brightness_pct is not None
                or update.api_v1_enabled is not None
            ):
                raise UnsupportedError(
                    "Setting status_led_brightness_pct and api_v1_enabled is not supported in v1"
                )

            data = update.to_dict()
            status, response = await self._request(
                "api/v1/system", method=METH_PUT, data=data
            )

        else:
            status, response = await self._request("api/v1/system")

        if status != HTTPStatus.OK:
            raise RequestError("Failed to get/set system")

        system = System.from_json(response)
        return system

    @optional_method
    async def identify(
        self,
    ) -> bool:
        """Send identify request."""

        if self._device is not None and self._device.supports_state is False:
            raise UnsupportedError("State is not supported")

        await self._request("api/v1/identify", method=METH_PUT)
        return True

    @backoff.on_exception(backoff.expo, RequestError, max_tries=3, logger=None)
    async def _request(
        self, path: str, method: str = METH_GET, data: object = None
    ) -> tuple[HTTPStatus, dict[str, Any] | None]:
        """Make a request to the API."""

        if self._session is None:
            self._session = ClientSession()
            self._close_session = True

        # Construct request
        url = f"http://{self.host}/{path}"
        headers = {"Content-Type": "application/json"}

        LOGGER.debug("%s, %s, %s", method, url, data)

        try:
            async with async_timeout.timeout(self._request_timeout):
                resp = await self._session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
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
            case HTTPStatus.FORBIDDEN:
                raise DisabledError(
                    "API disabled. API must be enabled in HomeWizard Energy app"
                )
            case HTTPStatus.NO_CONTENT:
                # No content, just return
                return (HTTPStatus.NO_CONTENT, None)
            case HTTPStatus.NOT_FOUND:
                raise NotFoundError("Resource not found")
            case HTTPStatus.OK:
                pass

        if resp.status != HTTPStatus.OK:
            # Something else went wrong
            raise RequestError(f"API request error ({resp.status})")

        return (resp.status, await resp.text())
