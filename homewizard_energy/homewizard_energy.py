"""HomeWizard Energy base class"""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp.client import ClientSession, ClientTimeout, TCPConnector

from .const import LOGGER
from .errors import UnsupportedError
from .models import CombinedModels, Device, Measurement, State, System


class HomeWizardEnergy:
    """Base class for HomeWizard Energy API."""

    _session: ClientSession | None = None
    _close_session: bool = False
    _request_timeout: int = 10
    _host: str

    _device: Device | None = None

    def __init__(
        self,
        host: str,
        clientsession: ClientSession = None,
        timeout: int = 10,
    ):
        """Create a HomeWizard Energy object.

        Args:
            host: IP or URL for device.
            clientsession: The clientsession.
            timeout: Request timeout in seconds.
        """
        self._host = host
        self._session = clientsession
        self._close_session = clientsession is None
        self._request_timeout = timeout

    @property
    def host(self) -> str:
        """Return the hostname of the device.

        Returns:
            host: The used host

        """
        return self._host

    async def combined(self) -> CombinedModels:
        """Get all information."""

        async def fetch_data(coroutine):
            try:
                return await coroutine
            except (UnsupportedError, NotImplementedError):
                return None

        device, measurement, system, state = await asyncio.gather(
            fetch_data(self.device()),
            fetch_data(self.measurement()),
            fetch_data(self.system()),
            fetch_data(self.state()),
        )

        return CombinedModels(
            device=device, measurement=measurement, system=system, state=state
        )

    async def device(self, reset_cache: bool = False) -> Device:
        """Get the device information."""
        raise NotImplementedError

    async def measurement(self) -> Measurement:
        """Get the current measurement."""
        raise NotImplementedError

    async def system(
        self,
        cloud_enabled: bool | None = None,
        status_led_brightness_pct: int | None = None,
        api_v1_enabled: bool | None = None,
    ) -> System:
        """Get/set the system."""
        raise NotImplementedError

    async def state(
        self,
        power_on: bool | None = None,
        switch_lock: bool | None = None,
        brightness: int | None = None,
    ) -> State:
        """Get/set the state."""
        raise UnsupportedError("State is not supported")

    async def identify(
        self,
    ) -> None:
        """Identify the device."""
        raise NotImplementedError

    async def reboot(
        self,
    ) -> None:
        """Reboot the device."""
        raise UnsupportedError("Reboot is not supported")

    async def close(self) -> None:
        """Close client session."""
        LOGGER.debug("Closing clientsession")
        if self._session and self._close_session:
            await self._session.close()

    async def _create_clientsession(self) -> None:
        """Create a client session."""

        if self._session is not None:
            raise RuntimeError("Session already exists")

        connector = TCPConnector(
            enable_cleanup_closed=True,
            limit_per_host=1,
        )

        self._close_session = True

        self._session = ClientSession(
            connector=connector, timeout=ClientTimeout(total=self._request_timeout)
        )

        # self._session = self._create_clientsession(connector, timeout=ClientTimeout(total=self._request_timeout))

    async def __aenter__(self) -> HomeWizardEnergy:
        """Async enter.

        Returns:
            The HomeWizardEnergy object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
            _exc_info: Exec type.
        """
        await self.close()
