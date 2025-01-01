"""HomeWizard Energy base class"""

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
from ..models import Device, Measurement, System, SystemUpdate, Token, State

from homewizard_energy.errors import (
    DisabledError,
    RequestError,
    ResponseError,
    UnauthorizedError,
)

class HomeWizardEnergy:
    """Base class for HomeWizard Energy API."""

    _clientsession: ClientSession | None = None
    _request_timeout: int = 10
    _host: str
    
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
        """Get the system information."""
        raise NotImplementedError
        
    async def state(self) -> State:
        """Get the current state."""
        raise NotImplementedError
    
    async def identify(
        self,
    ) -> None:
        """Identify the device."""
        raise NotImplementedError
    
    # async def reboot(
    #     self,
    # ) -> None:
    #     """Reboot the device."""
    #     raise NotImplementedError
