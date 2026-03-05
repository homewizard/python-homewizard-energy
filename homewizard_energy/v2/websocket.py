"""WebSocket client for HomeWizard Energy v2 API."""

from __future__ import annotations

import asyncio
import json
import random
import ssl
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from aiohttp import (
    ClientError,
    ClientSession,
    ClientTimeout,
    ClientWebSocketResponse,
    TCPConnector,
    WSMessage,
    WSMsgType,
)

from ..const import LOGGER
from ..errors import RequestError, UnauthorizedError
from ..models import Batteries, Device, Measurement, System
from .cacert import CACERT

TRANSIENT_PATTERNS = (
    "closed",
    "closing",
    "receive failed",
    "connection error",
    "connection reset",
    "connect failed",
    "timeout",
    "temporarily unavailable",
    "broken pipe",
    "eof",
)


class WebSocketTopic(StrEnum):
    """Known websocket topic names."""

    ALL = "*"
    DEVICE = "device"
    USER = "user"
    MEASUREMENT = "measurement"
    SYSTEM = "system"
    BATTERIES = "batteries"


@dataclass(frozen=True)
class HomeWizardEnergyWebSocketEvent:
    """Typed websocket event payload."""

    type: str
    data: Any
    raw: dict[str, Any]


class HomeWizardEnergyWebSocket:
    """Communicate with a HomeWizard Energy device over WebSocket."""

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def __init__(
        self,
        host: str,
        token: str | None,
        identifier: str | None = None,
        clientsession: ClientSession | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize the websocket client.

        Args:
            host: IP or URL for device.
            token: API token.
            identifier: Optional TLS hostname/CN identifier.
            clientsession: Optional shared aiohttp client session. The caller
                owns this session lifecycle and should keep it open while the
                websocket is active.
            timeout: Read/write timeout in seconds.
        """
        self._host = host
        self._token = token
        self._identifier = identifier
        self._session = clientsession
        self._close_session = clientsession is None
        self._request_timeout = timeout
        self._ssl: ssl.SSLContext | bool = False
        self._ws: ClientWebSocketResponse | None = None
        self._lock = asyncio.Lock()

    async def _get_ssl_context(self) -> ssl.SSLContext:
        """Build SSL context configured for HomeWizard certificates."""

        def _build_ssl_context() -> ssl.SSLContext:
            context = ssl.create_default_context(cadata=CACERT)
            context.verify_flags = ssl.VERIFY_X509_PARTIAL_CHAIN  # pylint: disable=no-member
            if self._identifier is not None:
                context.hostname_checks_common_name = True
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_REQUIRED
            return context

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _build_ssl_context)

    def _ensure_session_available(self) -> None:
        """Validate that a client session exists and is still open."""
        if self._session is None:
            raise RequestError("Client session is not initialized")

        if getattr(self._session, "closed", False) is True:
            if self._close_session:
                self._session = None
            raise RequestError(
                "Client session is closed; if using a shared session, keep it open while websocket is active"
            )

    async def _create_clientsession(self) -> None:
        """Create a client session configured like the HTTP API client."""
        if self._session is not None:
            raise RuntimeError("Session already exists")  # pragma: no cover

        connector = TCPConnector(
            enable_cleanup_closed=True,
            limit_per_host=1,
        )

        self._close_session = True
        self._session = ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=self._request_timeout),
        )

    async def _close_ws(self, ws: ClientWebSocketResponse | None) -> None:
        """Close a websocket instance when present."""
        if ws is not None:
            await ws.close()

    async def _reset_ws(self) -> None:
        """Close and clear the current websocket reference."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def connect(self) -> None:
        """Connect and authenticate the websocket session."""
        if self._token is None:
            raise UnauthorizedError("Token missing")

        async with self._lock:
            if self._session is None:
                await self._create_clientsession()

            self._ensure_session_available()

            if self._ssl is False:
                self._ssl = await self._get_ssl_context()

            if self._ws is not None and not self._ws.closed:
                return

            url = f"wss://{self._host}/api/ws"
            LOGGER.debug("Connecting websocket: %s", url)
            ws: ClientWebSocketResponse | None = None
            try:
                ws = await self._session.ws_connect(
                    url,
                    ssl=self._ssl,
                    heartbeat=30,
                    server_hostname=self._identifier,
                )

                msg = await self._receive_message(timeout=40, ws=ws)
                if msg.get("type") != "authorization_requested":
                    raise RequestError("WebSocket authorization was not requested")

                await self._send_internal("authorization", self._token, ws=ws)

                msg = await self._receive_message(timeout=10, ws=ws)
                if msg.get("type") != "authorized":
                    raise RequestError("WebSocket authorization failed")

                self._ws = ws
            except (ClientError, asyncio.TimeoutError) as ex:
                await self._close_ws(ws)
                await self._reset_ws()
                raise RequestError(
                    f"Error occurred while communicating with the HomeWizard Energy device at {self._host}"
                ) from ex
            except RequestError:
                await self._close_ws(ws)
                await self._reset_ws()
                raise
            except Exception as ex:
                LOGGER.debug(
                    "Unexpected websocket error during connect/auth (%s): %s",
                    ex.__class__.__name__,
                    ex,
                )
                await self._close_ws(ws)
                await self._reset_ws()
                raise RequestError(
                    f"Error occurred while communicating with the HomeWizard Energy device at {self._host}"
                ) from ex

    async def close(self) -> None:
        """Close websocket and optionally owned client session."""
        async with self._lock:
            await self._reset_ws()

            if self._session is not None and self._close_session:
                await self._session.close()
                self._session = None

    async def _receive_ws_message(
        self,
        timeout: float | None = None,
        ws: ClientWebSocketResponse | None = None,
    ) -> WSMessage:
        """Receive a raw websocket message."""
        self._ensure_session_available()

        websocket = ws or self._ws
        if websocket is None:
            raise RequestError("WebSocket is not connected")

        try:
            return await websocket.receive(timeout=timeout)
        except (ClientError, asyncio.TimeoutError, RuntimeError) as ex:
            raise RequestError("WebSocket receive failed") from ex

    async def _receive_message(
        self,
        timeout: float | None = None,
        ws: ClientWebSocketResponse | None = None,
    ) -> dict[str, Any]:
        """Receive and validate a JSON websocket message."""
        msg = await self._receive_ws_message(timeout=timeout, ws=ws)

        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError as ex:
                raise RequestError("Received invalid websocket JSON message") from ex

            if not isinstance(data, dict):
                raise RequestError(
                    "Received invalid websocket payload shape: expected JSON object"
                )

            if data.get("type") == "error":
                payload = data.get("data")
                payload_dict = payload if isinstance(payload, dict) else {}
                error = payload_dict.get("message", "Unknown websocket error")
                raise RequestError(error)

            return data

        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
            raise RequestError("WebSocket connection closed")

        if msg.type == WSMsgType.ERROR:
            raise RequestError("WebSocket connection error")

        raise RequestError(f"Unexpected websocket message type: {msg.type}")

    @staticmethod
    def _decode_event_data(event_type: str, payload: Any) -> Any:
        """Decode known event payloads into typed models."""
        if not isinstance(payload, dict):
            return payload

        model_map: dict[str, type] = {
            WebSocketTopic.DEVICE.value: Device,
            WebSocketTopic.MEASUREMENT.value: Measurement,
            WebSocketTopic.SYSTEM.value: System,
            WebSocketTopic.BATTERIES.value: Batteries,
        }

        model_cls = model_map.get(event_type)
        if model_cls is None:
            return payload

        try:
            return model_cls.from_dict(payload)
        except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover
            LOGGER.debug("Failed to decode websocket event type %s", event_type)
            return payload

    async def receive(self) -> dict[str, Any]:
        """Receive a decoded websocket message."""
        return await self._receive_message(timeout=None)

    async def receive_typed(self) -> HomeWizardEnergyWebSocketEvent:
        """Receive a typed websocket event."""
        raw = await self.receive()
        event_type = str(raw.get("type", ""))
        payload = raw.get("data")
        data = self._decode_event_data(event_type, payload)
        return HomeWizardEnergyWebSocketEvent(type=event_type, data=data, raw=raw)

    async def _send_internal(
        self,
        message_type: str,
        data: Any = None,
        ws: ClientWebSocketResponse | None = None,
    ) -> None:
        """Send a websocket command without reconnecting."""
        self._ensure_session_available()

        websocket = ws or self._ws
        if websocket is None or websocket.closed:
            raise RequestError("WebSocket is not connected")

        payload: dict[str, Any] = {"type": message_type}
        if data is not None:
            payload["data"] = data

        try:
            await websocket.send_json(payload)
        except (ClientError, asyncio.TimeoutError) as ex:
            raise RequestError("WebSocket send failed") from ex

    async def send(self, message_type: str, data: Any = None) -> None:
        """Send a websocket command."""
        await self.connect()
        await self._send_internal(message_type, data)

    async def subscribe(self, topic: str | WebSocketTopic) -> None:
        """Subscribe to a websocket topic."""
        await self.send("subscribe", str(topic))

    async def unsubscribe(self, topic: str | WebSocketTopic) -> None:
        """Unsubscribe from a websocket topic."""
        await self.send("unsubscribe", str(topic))

    async def identify(self) -> None:
        """Blink device LED via websocket identify command."""
        await self.send("identify")

    async def request(self, message_type: str | WebSocketTopic) -> None:
        """Request latest state for a topic once."""
        await self.send(str(message_type))

    @staticmethod
    def _is_transient_error(error: RequestError) -> bool:
        """Return True when an error likely indicates a recoverable disconnect."""
        message = str(error).lower()

        if any(pattern in message for pattern in TRANSIENT_PATTERNS):
            return True

        cause = error.__cause__
        if isinstance(cause, (ClientError, asyncio.TimeoutError, TimeoutError)):
            return True

        cause_message = str(cause).lower() if cause is not None else ""
        return any(pattern in cause_message for pattern in TRANSIENT_PATTERNS)

    async def events(self, reconnect: bool = False) -> AsyncIterator[dict[str, Any]]:
        """Yield websocket messages.

        Args:
            reconnect: Automatically reconnect when the socket is dropped.
        """
        retry = 0
        while True:
            try:
                if self._ws is None or self._ws.closed:
                    await self.connect()

                event = await self.receive()
                retry = 0
                yield event
            except RequestError as ex:
                should_reconnect = reconnect and self._is_transient_error(ex)

                message = str(ex).lower()
                external_session_closed = (
                    not self._close_session
                    and self._session is not None
                    and getattr(self._session, "closed", False) is True
                )
                if should_reconnect and "closed" in message and external_session_closed:
                    should_reconnect = False

                if not should_reconnect:
                    raise

                retry += 1
                backoff_seconds = min(2**retry, 30)
                jitter_factor = random.uniform(0.8, 1.2)  # nosec B311
                backoff_seconds = min(backoff_seconds * jitter_factor, 30)
                LOGGER.debug(
                    "WebSocket disconnected, reconnecting in %.2f seconds",
                    backoff_seconds,
                )

                async with self._lock:
                    await self._reset_ws()

                await asyncio.sleep(backoff_seconds)

    async def events_typed(
        self, reconnect: bool = False
    ) -> AsyncIterator[HomeWizardEnergyWebSocketEvent]:
        """Yield websocket events with best-effort typed payloads."""
        async for event in self.events(reconnect=reconnect):
            event_type = str(event.get("type", ""))
            payload = event.get("data")
            yield HomeWizardEnergyWebSocketEvent(
                type=event_type,
                data=self._decode_event_data(event_type, payload),
                raw=event,
            )

    async def __aenter__(self) -> HomeWizardEnergyWebSocket:
        """Connect websocket on enter."""
        await self.connect()
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Close websocket on exit."""
        await self.close()
