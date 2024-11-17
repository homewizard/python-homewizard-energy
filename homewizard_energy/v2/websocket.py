"""Websocket client for HomeWizard Energy API."""

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

import aiohttp

from homewizard_energy.errors import UnauthorizedError

from .const import WebsocketTopic
from .models import Device, Measurement, System

if TYPE_CHECKING:
    from . import HomeWizardEnergyV2

OnMessageCallbackType = Callable[[str, Device | Measurement | System], None]

_LOGGER = logging.getLogger(__name__)


class Websocket:
    """Websocket client for HomeWizard Energy API."""

    _connect_lock: asyncio.Lock = asyncio.Lock()
    _ws_connection: aiohttp.ClientWebSocketResponse | None = None
    _ws_subscriptions: list[tuple[str, OnMessageCallbackType]] = []

    _ws_authenticated: bool = False

    def __init__(self, parent: "HomeWizardEnergyV2"):
        self._parent = parent

    async def connect(self) -> bool:
        """Connect the websocket."""

        if self._connect_lock.locked():
            _LOGGER.debug("Another connect is already happening")
            return False
        try:
            await asyncio.wait_for(self._connect_lock.acquire(), timeout=0.1)
        except asyncio.TimeoutError:
            _LOGGER.debug("Failed to get connection lock")

        start_event = asyncio.Event()
        _LOGGER.debug("Scheduling WS connect...")
        asyncio.create_task(self._websocket_loop(start_event))

        try:
            await asyncio.wait_for(
                start_event.wait(), timeout=self._parent.request_timeout
            )
        except asyncio.TimeoutError:
            _LOGGER.warning("Timed out while waiting for Websocket to connect")
            await self.disconnect()

        self._connect_lock.release()
        if self._ws_connection is None:
            _LOGGER.debug("Failed to connect to Websocket")
            return False
        _LOGGER.debug("Connected to Websocket successfully")
        return True

    async def disconnect(self) -> None:
        """Disconnect the websocket."""
        if self._ws_connection is not None and not self._ws_connection.closed:
            await self._ws_connection.close()
        self._ws_connection = None

    def subscribe(
        self, topic: WebsocketTopic, ws_callback: OnMessageCallbackType
    ) -> Callable[[], None]:
        """
        Subscribe to raw websocket messages.

        Returns a callback that will unsubscribe.
        """

        def _unsub_ws_callback() -> None:
            self._ws_subscriptions.remove({topic, ws_callback})

        _LOGGER.debug("Adding subscription: %s, %s", topic, ws_callback)
        self._ws_subscriptions.append((topic, ws_callback))

        if self._ws_connection is not None and self._ws_authenticated:
            asyncio.create_task(
                self._ws_connection.send_json({"type": "subscribe", "data": topic})
            )

        return _unsub_ws_callback

    async def _websocket_loop(self, start_event: asyncio.Event) -> None:
        _LOGGER.debug("Connecting WS...")

        _clientsession = await self._parent.get_clientsession()

        # catch any and all errors for Websocket so we can clean up correctly
        try:
            self._ws_connection = await _clientsession.ws_connect(
                f"wss://{self._parent.host}/api/ws", ssl=False
            )
            start_event.set()

            async for msg in self._ws_connection:
                _LOGGER.info("Received message: %s", msg)
                if not await self._process_message(msg):
                    break
        except aiohttp.ClientError as e:
            _LOGGER.exception("Websocket disconnect error: %s", e)
        finally:
            _LOGGER.debug("Websocket disconnected")
            if self._ws_connection is not None and not self._ws_connection.closed:
                await self._ws_connection.close()
            self._ws_connection = None
            # make sure event does not timeout
            start_event.set()

    async def _on_authorization_requested(self, msg_type: str, msg_data: str) -> None:
        del msg_type, msg_data

        _LOGGER.info("Authorization requested")
        if self._ws_authenticated:
            raise UnauthorizedError("Already authenticated")

        await self._ws_connection.send_json(
            {"type": "authorization", "data": self._parent.token}
        )

    async def _on_authorized(self, msg_type: str, msg_data: str) -> None:
        del msg_type, msg_data

        _LOGGER.info("Authorized")
        self._ws_authenticated = True

        # Send subscription requests
        print(self._ws_subscriptions)
        for topic, _ in self._ws_subscriptions:
            _LOGGER.info("Sending subscription request for %s", topic)
            await self._ws_connection.send_json({"type": "subscribe", "data": topic})

    async def _process_message(self, msg: aiohttp.WSMessage) -> bool:
        if msg.type == aiohttp.WSMsgType.ERROR:
            raise ValueError(f"Error from Websocket: {msg.data}")

        _LOGGER.debug("Received message: %s", msg.data)

        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                msg = msg.json()
            except ValueError as ex:
                raise ValueError(f"Invalid JSON received: {msg.data}") from ex

            if "type" not in msg:
                raise ValueError(f"Missing 'type' in message: {msg}")

            msg_type = msg.get("type")
            msg_data = msg.get("data")
            parsed_data = None

            match msg_type:
                case "authorization_requested":
                    await self._on_authorization_requested(msg_type, msg_data)
                    return True

                case "authorized":
                    await self._on_authorized(msg_type, msg_data)
                    return True

                case WebsocketTopic.MEASUREMENT:
                    parsed_data = Measurement.from_dict(msg_data)

                case WebsocketTopic.SYSTEM:
                    parsed_data = System.from_dict(msg_data)

                case WebsocketTopic.DEVICE:
                    parsed_data = Device.from_dict(msg_data)

            if parsed_data is None:
                raise ValueError(f"Unknown message type: {msg_type}")

            for topic, callback in self._ws_subscriptions:
                if topic == msg_type:
                    try:
                        await callback(topic, parsed_data)
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.exception("Error processing websocket message")

        return True
