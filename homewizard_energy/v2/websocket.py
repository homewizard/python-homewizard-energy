"""WebSocket client for the HomeWizard Energy v2 API."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from aiohttp import (
    ClientError,
    ClientSession,
    ClientWebSocketResponse,
    TCPConnector,
    WSMsgType,
    WSServerHandshakeError,
)

from ..const import LOGGER
from ..errors import (
    RequestError,
    ResponseError,
    UnauthorizedError,
    UnsupportedError,
    WebSocketDisconnectedError,
)
from ..models import Batteries, Device, Measurement, System

if TYPE_CHECKING:
    from . import HomeWizardEnergyV2

# Interval in seconds for sending a ping to the device. The connection is
# considered lost when the device does not answer within half this interval.
HEARTBEAT_INTERVAL = 30

# Longest time in seconds to wait between two attempts to reconnect
MAX_RECONNECT_BACKOFF = 30

ERROR_UNAUTHORIZED = "user:unauthorized"


class WebSocketTopic(StrEnum):
    """Topics that can be subscribed to or requested."""

    ALL = "*"
    DEVICE = "device"
    USER = "user"
    MEASUREMENT = "measurement"
    SYSTEM = "system"
    BATTERIES = "batteries"


@dataclass(frozen=True)
class HomeWizardEnergyWebSocketEvent:
    """Message received from the device.

    This class is used as-is for messages that have no model, such as `user`,
    and for messages that could not be decoded. In that case `data` is the same
    as the `data` field of the raw message. Known topics use a subclass, where
    `data` is always the model.
    """

    type: str
    data: Any
    raw: dict[str, Any]


@dataclass(frozen=True)
class DeviceEvent(HomeWizardEnergyWebSocketEvent):
    """Update for the `device` topic."""

    data: Device


@dataclass(frozen=True)
class MeasurementEvent(HomeWizardEnergyWebSocketEvent):
    """Update for the `measurement` topic."""

    data: Measurement


@dataclass(frozen=True)
class SystemEvent(HomeWizardEnergyWebSocketEvent):
    """Update for the `system` topic."""

    data: System


@dataclass(frozen=True)
class BatteriesEvent(HomeWizardEnergyWebSocketEvent):
    """Update for the `batteries` topic."""

    data: Batteries


@dataclass(frozen=True)
class ErrorEvent(HomeWizardEnergyWebSocketEvent):
    """Error sent by the device in response to a command.

    The device does not tell which command caused the error, and the
    connection stays open.
    """

    data: str

    @property
    def message(self) -> str:
        """Return the error, such as `request:unknown-subscription`."""
        return self.data


_EVENTS: dict[str, tuple[type[HomeWizardEnergyWebSocketEvent], type]] = {
    WebSocketTopic.DEVICE: (DeviceEvent, Device),
    WebSocketTopic.MEASUREMENT: (MeasurementEvent, Measurement),
    WebSocketTopic.SYSTEM: (SystemEvent, System),
    WebSocketTopic.BATTERIES: (BatteriesEvent, Batteries),
}


def _error_message(message: dict[str, Any]) -> str:
    """Return the error description of an `error` message."""
    data = message.get("data")
    if isinstance(data, dict):
        return str(data.get("message", "Unknown error"))
    return "Unknown error"


def _to_event(raw: dict[str, Any]) -> HomeWizardEnergyWebSocketEvent:
    """Convert a raw message to an event."""
    event_type = str(raw.get("type", ""))
    data = raw.get("data")

    if event_type == "error":
        return ErrorEvent(type=event_type, data=_error_message(raw), raw=raw)

    if event_type in _EVENTS and isinstance(data, dict):
        event_cls, model_cls = _EVENTS[event_type]
        try:
            return event_cls(type=event_type, data=model_cls.from_dict(data), raw=raw)
        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.warning(
                "Failed to decode WebSocket message of type '%s'", event_type
            )

    return HomeWizardEnergyWebSocketEvent(type=event_type, data=data, raw=raw)


class HomeWizardEnergyWebSocket:
    """Receive real-time updates from a HomeWizard Energy device.

    Create this object with `HomeWizardEnergyV2.websocket()`.
    """

    def __init__(
        self,
        api: HomeWizardEnergyV2,
        on_connection_change: Callable[[bool], None] | None = None,
    ) -> None:
        """Create the WebSocket client.

        Args:
            api: API client of the device. Host, token, identifier and timeout
                are taken from this client. A client session that was passed to
                the API client is used for the WebSocket as well.
            on_connection_change: Called with `True` when the WebSocket is
                connected and authorized, and with `False` when the connection
                is lost or closed.
        """
        self._api = api
        self._on_connection_change = on_connection_change

        self._session: ClientSession | None = None
        self._ws: ClientWebSocketResponse | None = None
        self._subscriptions: set[str] = set()
        self._reported_connected = False

        self._lock = asyncio.Lock()
        self._closed = asyncio.Event()

    @property
    def connected(self) -> bool:
        """Return True when the WebSocket is connected and authorized."""
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        """Connect, authorize and subscribe to the topics subscribed to earlier.

        Does nothing when already connected.

        Raises:
            UnauthorizedError: No token is set, or the device rejected it.
            UnsupportedError: The device has no WebSocket, see
                `Device.supports_websocket()`.
            WebSocketDisconnectedError: The device could not be reached.
            RequestError: The device did not follow the expected flow.
        """
        async with self._lock:
            self._closed.clear()
            await self._connect()

    async def close(self) -> None:
        """Close the WebSocket.

        This also ends `events()` and `events_typed()`.
        """
        self._closed.set()
        async with self._lock:
            await self._disconnect(self._ws)
            await self._close_session()

    async def send(self, message_type: str, data: Any = None) -> None:
        """Send a message to the device. Connects first when needed."""
        await self.connect()
        await self._send(self._ws, message_type, data)

    async def subscribe(self, topic: str | WebSocketTopic) -> None:
        """Subscribe to a topic. Connects first when needed.

        The subscription is restored after a reconnect.
        """
        topic = str(topic)
        self._subscriptions.add(topic)
        if self.connected:
            await self._send(self._ws, "subscribe", topic)
        else:
            # Connecting subscribes to all topics
            await self.connect()

    async def unsubscribe(self, topic: str | WebSocketTopic) -> None:
        """Unsubscribe from a topic."""
        topic = str(topic)
        self._subscriptions.discard(topic)
        if self.connected:
            await self._send(self._ws, "unsubscribe", topic)

    async def request(self, topic: str | WebSocketTopic) -> None:
        """Ask the device to send the latest data of a topic once."""
        await self.send(str(topic))

    async def identify(self) -> None:
        """Let the status light of the device blink for a few seconds."""
        await self.send("identify")

    async def receive(self) -> dict[str, Any]:
        """Wait for the next message and return it as received.

        Raises:
            WebSocketDisconnectedError: Not connected, or the connection was lost.
            ResponseError: The message is not a JSON object.
        """
        ws = self._ws
        try:
            return await self._receive(ws)
        except WebSocketDisconnectedError:
            await self._disconnect(ws)
            raise

    async def receive_typed(self) -> HomeWizardEnergyWebSocketEvent:
        """Wait for the next message and return it as an event."""
        return _to_event(await self.receive())

    async def events(self, reconnect: bool = False) -> AsyncIterator[dict[str, Any]]:
        """Yield messages as received, until `close()` is called.

        Connects first when needed. Errors sent by the device are yielded as a
        message with type `error`.

        Args:
            reconnect: Connect and subscribe again when the connection is lost
                or the device can't be reached, instead of raising
                `WebSocketDisconnectedError`. Other errors, such as a rejected
                token, are always raised.
        """
        retry = 0
        while not self._closed.is_set():
            ws = self._ws
            try:
                if ws is None or ws.closed:
                    ws = await self._connect_unless_closed()
                    if ws is None:
                        return
                try:
                    message = await self._receive(ws)
                except ResponseError as ex:
                    LOGGER.warning("Ignoring WebSocket message: %s", ex)
                    continue
            except WebSocketDisconnectedError as ex:
                await self._disconnect(ws)
                if self._closed.is_set():
                    return
                if not reconnect:
                    raise

                retry += 1
                delay = min(2**retry, MAX_RECONNECT_BACKOFF)
                delay *= random.uniform(0.8, 1.0)  # nosec B311
                LOGGER.debug(
                    "WebSocket of %s disconnected (%s), reconnecting in %.1f seconds",
                    self._api.host,
                    ex,
                    delay,
                )
                # Stop waiting as soon as the WebSocket gets closed
                with suppress(TimeoutError):
                    async with asyncio.timeout(delay):
                        await self._closed.wait()
                continue

            retry = 0
            yield message

    async def events_typed(
        self, reconnect: bool = False
    ) -> AsyncIterator[HomeWizardEnergyWebSocketEvent]:
        """Yield messages as events, until `close()` is called.

        Known topics are yielded as `DeviceEvent`, `MeasurementEvent`,
        `SystemEvent` or `BatteriesEvent`, and errors as `ErrorEvent`. See
        `events()` for the other behavior.
        """
        async for message in self.events(reconnect=reconnect):
            yield _to_event(message)

    async def _connect_unless_closed(self) -> ClientWebSocketResponse | None:
        """Connect, unless `close()` was called in the meantime."""
        async with self._lock:
            if self._closed.is_set():
                return None
            await self._connect()
            return self._ws

    async def _connect(self) -> None:
        """Connect, authorize and subscribe. Must be called while holding the lock."""
        if self.connected:
            return

        try:
            self._ws = await self._open()
        except BaseException:
            await self._close_session()
            raise

        self._report_connected(True)

    async def _open(self) -> ClientWebSocketResponse:
        """Open a connection, authorize and subscribe."""
        # pylint: disable=protected-access
        api = self._api
        token = api._token
        if token is None:
            raise UnauthorizedError("Token missing")

        try:
            device = await api.device()
        except RequestError as ex:
            raise WebSocketDisconnectedError(
                f"Unable to get the device information of {api.host}"
            ) from ex
        if not device.supports_websocket():
            raise UnsupportedError("Device has no WebSocket")

        session = self._get_session()
        ssl_context = await api._get_ssl()
        url = f"wss://{api.host}/api/ws"
        LOGGER.debug("Connecting to WebSocket: %s", url)

        try:
            async with asyncio.timeout(api._request_timeout):
                ws = await session.ws_connect(
                    url,
                    ssl=ssl_context,
                    heartbeat=HEARTBEAT_INTERVAL,
                    server_hostname=api._identifier,
                )
        except WSServerHandshakeError as ex:
            if ex.status == HTTPStatus.NOT_FOUND:
                raise UnsupportedError("Device has no WebSocket") from ex
            if ex.status == HTTPStatus.UNAUTHORIZED:
                raise UnauthorizedError("Token rejected") from ex
            raise WebSocketDisconnectedError(
                f"WebSocket of {api.host} refused the connection: {ex.status}"
            ) from ex
        except (ClientError, OSError, TimeoutError) as ex:
            raise WebSocketDisconnectedError(
                f"Unable to connect to the WebSocket of {api.host}"
            ) from ex

        try:
            await self._authorize(ws, token)
            for topic in sorted(self._subscriptions):
                await self._send(ws, "subscribe", topic)
        except BaseException:
            await ws.close()
            raise

        return ws

    async def _authorize(self, ws: ClientWebSocketResponse, token: str) -> None:
        """Wait for the authorization request of the device and answer it."""
        timeout = self._api._request_timeout  # pylint: disable=protected-access

        message = await self._receive(ws, timeout)
        if message.get("type") != "authorization_requested":
            raise RequestError(
                f"Expected an authorization request, got: {message.get('type')}"
            )

        await self._send(ws, "authorization", token)

        try:
            message = await self._receive(ws, timeout)
        except WebSocketDisconnectedError as ex:
            if ex.close_code is not None:
                # Device closes the connection when it does not accept the token
                raise UnauthorizedError("Token rejected") from ex
            raise
        if message.get("type") == "error":
            error = _error_message(message)
            if error == ERROR_UNAUTHORIZED:
                raise UnauthorizedError("Token rejected")
            raise RequestError(f"WebSocket authorization failed: {error}")
        if message.get("type") != "authorized":
            raise RequestError(f"Expected to be authorized, got: {message.get('type')}")

    def _get_session(self) -> ClientSession:
        """Return the session to use for the WebSocket."""
        # pylint: disable=protected-access
        api = self._api
        if api._session is not None and not api._close_session:
            # Session was provided by the user of the API client
            if api._session.closed:
                raise RequestError("Client session is closed")
            return api._session

        # The session that the API client creates for itself is limited to one
        # connection, and that connection would be taken by the WebSocket. HTTP
        # requests would then wait forever, so use a separate session.
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                connector=TCPConnector(enable_cleanup_closed=True, limit=1)
            )
        return self._session

    async def _close_session(self) -> None:
        """Close the session, when the WebSocket has its own."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _disconnect(self, ws: ClientWebSocketResponse | None) -> None:
        """Close a connection, and forget it when it is the current one."""
        if ws is not None and ws is self._ws:
            self._ws = None
        if self._ws is None:
            self._report_connected(False)
        if ws is not None:
            await ws.close()

    def _report_connected(self, connected: bool) -> None:
        """Report a change of the connection state."""
        if connected == self._reported_connected:
            return
        self._reported_connected = connected

        if self._on_connection_change is None:
            return
        try:
            self._on_connection_change(connected)
        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception("Error in WebSocket connection change callback")

    @staticmethod
    async def _send(
        ws: ClientWebSocketResponse | None, message_type: str, data: Any = None
    ) -> None:
        """Send a message over a connection."""
        if ws is None or ws.closed:
            raise WebSocketDisconnectedError("WebSocket is not connected")

        message: dict[str, Any] = {"type": message_type}
        if data is not None:
            message["data"] = data

        try:
            await ws.send_json(message)
        except (ClientError, OSError, TimeoutError) as ex:
            raise WebSocketDisconnectedError("Failed to send to WebSocket") from ex

    @staticmethod
    async def _receive(
        ws: ClientWebSocketResponse | None, timeout: float | None = None
    ) -> dict[str, Any]:
        """Receive a message from a connection."""
        if ws is None or ws.closed:
            raise WebSocketDisconnectedError("WebSocket is not connected")

        try:
            msg = await ws.receive(timeout)
        except (ClientError, OSError, TimeoutError) as ex:
            raise WebSocketDisconnectedError("Failed to receive from WebSocket") from ex

        if msg.type is WSMsgType.CLOSE:
            raise WebSocketDisconnectedError(
                f"WebSocket connection closed by device with code {msg.data}",
                close_code=msg.data,
            )

        if msg.type in (WSMsgType.CLOSING, WSMsgType.CLOSED):
            raise WebSocketDisconnectedError("WebSocket connection closed")

        if msg.type is WSMsgType.ERROR:
            raise WebSocketDisconnectedError(
                f"WebSocket connection failed: {msg.data!r}"
            )

        if msg.type is not WSMsgType.TEXT:
            raise ResponseError(f"Unexpected WebSocket message type: {msg.type!r}")

        try:
            message = json.loads(msg.data)
        except json.JSONDecodeError as ex:
            raise ResponseError("WebSocket message is not valid JSON") from ex

        if not isinstance(message, dict):
            raise ResponseError("WebSocket message is not a JSON object")

        return message

    async def __aenter__(self) -> HomeWizardEnergyWebSocket:
        """Connect on enter."""
        try:
            await self.connect()
        except BaseException:
            await self.close()
            raise
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Close on exit."""
        await self.close()
