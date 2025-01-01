"""HomeWizard Energy base class"""

from __future__ import annotations

from typing import Any

from aiohttp.client import ClientSession

from .const import LOGGER
from .models import Device, Measurement, State, StateUpdate, System, SystemUpdate


class HomeWizardEnergy:
    """Base class for HomeWizard Energy API."""

    _session: ClientSession | None = None
    _close_session: bool = False
    _request_timeout: int = 10
    _host: str

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

    async def device(self) -> Device:
        """Get the device information."""
        raise NotImplementedError

    async def measurement(self) -> Measurement:
        """Get the current measurement."""
        raise NotImplementedError

    async def system(
        self,
        update: SystemUpdate | None = None,
    ) -> System:
        """Get/set the system."""
        raise NotImplementedError

    async def state(
        self,
        update: StateUpdate | None = None,
    ) -> State:
        """Get/set the state."""
        raise NotImplementedError

    async def identify(
        self,
    ) -> None:
        """Identify the device."""
        raise NotImplementedError

    async def reboot(
        self,
    ) -> None:
        """Reboot the device."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close client session."""
        LOGGER.debug("Closing clientsession")
        if self._session and self._close_session:
            await self._session.close()

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
