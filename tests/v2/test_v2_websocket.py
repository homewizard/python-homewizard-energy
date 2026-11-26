"""Test the WebSocket of the v2 API, against a local server that acts as a device."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import pytest
from aiohttp import ClientConnectionError, ClientSession, WSMsgType, web
from aiohttp.test_utils import TestServer

from homewizard_energy import HomeWizardEnergyV2
from homewizard_energy.errors import (
    RequestError,
    ResponseError,
    UnauthorizedError,
    UnsupportedError,
    WebSocketDisconnectedError,
)
from homewizard_energy.models import Batteries, Device, Measurement, System
from homewizard_energy.v2 import websocket as websocket_module
from homewizard_energy.v2.websocket import (
    BatteriesEvent,
    DeviceEvent,
    ErrorEvent,
    HomeWizardEnergyWebSocket,
    HomeWizardEnergyWebSocketEvent,
    MeasurementEvent,
    SystemEvent,
    WebSocketTopic,
)

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]

TOKEN = "valid-token"

AUTHORIZATION_REQUESTED = {
    "type": "authorization_requested",
    "data": {"api_version": "2.0.0"},
}

TOPICS = {
    "device": json.loads(load_fixtures("HWE-P1/device.json")),
    "measurement": json.loads(load_fixtures("HWE-P1/measurement_1_phase_no_gas.json")),
    "system": json.loads(load_fixtures("HWE-P1/system.json")),
    "batteries": json.loads(load_fixtures("HWE-P1/batteries.json")),
    "user": [{"name": "local/test", "current": True}],
}


class FakeDevice:
    """Device that follows the documented flow of `/api/ws`."""

    def __init__(self) -> None:
        """Create the device."""
        # Status to answer the upgrade request with, instead of accepting it
        self.status: int | None = None
        # First message to send, None to stay silent
        self.greeting: dict[str, Any] | None = AUTHORIZATION_REQUESTED
        # Answer to a valid token
        self.authorized: dict[str, Any] = {"type": "authorized"}
        # Answer to an invalid token, None to drop the connection
        self.unauthorized: dict[str, Any] | None = None

        self.attempts = 0
        self.connections: list[web.WebSocketResponse] = []
        self.received: list[list[dict[str, Any]]] = []

    @property
    def connection(self) -> web.WebSocketResponse:
        """Return the most recent connection."""
        return self.connections[-1]

    async def handle(self, request: web.Request) -> web.StreamResponse:
        """Handle a connection to `/api/ws`."""
        self.attempts += 1
        if self.status is not None:
            return web.Response(status=self.status)

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        received: list[dict[str, Any]] = []
        self.connections.append(ws)
        self.received.append(received)

        if self.greeting is not None:
            await ws.send_json(self.greeting)

        async for msg in ws:
            message = json.loads(msg.data)
            received.append(message)
            await self._answer(ws, message)

        return ws

    async def _answer(self, ws: web.WebSocketResponse, message: dict[str, Any]) -> None:
        """Answer a message of the client."""
        match message["type"], message.get("data"):
            case "authorization", token if token == TOKEN:
                await ws.send_json(self.authorized)
            case "authorization", _ if self.unauthorized is None:
                # This is what a P1 Meter does (firmware 6.0503)
                ws._req.transport.abort()  # pylint: disable=protected-access
            case "authorization", _:
                await ws.send_json(self.unauthorized)
            case "subscribe", "*":
                for topic, data in TOPICS.items():
                    await ws.send_json({"type": topic, "data": data})
            case "subscribe", topic if topic in TOPICS:
                await ws.send_json({"type": topic, "data": TOPICS[topic]})
            case "subscribe", _:
                await self.send_error(ws, "request:unknown-subscription")
            case "unsubscribe" | "identify", _:
                pass
            case topic, None if topic in TOPICS:
                await ws.send_json({"type": topic, "data": TOPICS[topic]})
            case _:
                await self.send_error(ws, "request:unknown-type")

    async def send_error(self, ws: web.WebSocketResponse, error: str) -> None:
        """Send an error."""
        await ws.send_json({"type": "error", "data": {"message": error}})

    async def wait_for(self, attempts: int) -> None:
        """Wait until the client tried to connect a number of times."""
        async with asyncio.timeout(5):
            while self.attempts < attempts:
                await asyncio.sleep(0.01)


@pytest.fixture(name="device")
async def device_fixture(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FakeDevice]:
    """Run a fake device, and send all WebSocket connections to it."""
    device = FakeDevice()
    app = web.Application()
    app.router.add_get("/api/ws", device.handle)
    server = TestServer(app)
    await server.start_server()

    ws_connect = ClientSession.ws_connect

    def ws_connect_to_fake_device(self, url, *, ssl, server_hostname, **kwargs):
        """Connect to the fake device, without TLS."""
        assert str(url) == "wss://example.com/api/ws"
        assert ssl is not None
        assert server_hostname is None
        return ws_connect(self, server.make_url("/api/ws"), **kwargs)

    monkeypatch.setattr(ClientSession, "ws_connect", ws_connect_to_fake_device)
    # Reconnect without delay
    monkeypatch.setattr(websocket_module, "MAX_RECONNECT_BACKOFF", 0.01)

    yield device

    await server.close()


@pytest.fixture(name="api")
async def api_fixture() -> AsyncIterator[HomeWizardEnergyV2]:
    """Return an API client with a valid token."""
    async with HomeWizardEnergyV2("example.com", token=TOKEN, timeout=1) as api:
        # Device information is known, so no HTTP request is needed for it
        api._device = Device.from_dict(TOPICS["device"])  # pylint: disable=protected-access
        yield api


async def test_connect_requires_token():
    """Test connecting without token."""
    async with HomeWizardEnergyV2("example.com") as api:
        ws = api.websocket()

        with pytest.raises(UnauthorizedError, match="Token missing"):
            await ws.connect()

        assert not ws.connected


async def test_connect_authorizes_with_token(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test the authorization flow."""
    states: list[bool] = []
    ws = api.websocket(on_connection_change=states.append)
    assert not ws.connected

    await ws.connect()

    assert ws.connected
    assert device.received == [[{"type": "authorization", "data": TOKEN}]]
    assert states == [True]

    # Connecting again does nothing
    await ws.connect()
    assert device.attempts == 1
    assert states == [True]

    await ws.close()

    assert not ws.connected
    assert states == [True, False]

    # Closing again does nothing
    await ws.close()
    assert states == [True, False]


async def test_context_manager(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test connecting and closing with the context manager."""
    async with api.websocket() as ws:
        assert ws.connected
        assert device.attempts == 1

    assert not ws.connected


async def test_connect_uses_token_of_api(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test a token that is set on the API client after creating the WebSocket."""
    api._token = None  # pylint: disable=protected-access
    ws = api.websocket()
    api._token = TOKEN  # pylint: disable=protected-access

    await ws.connect()

    assert ws.connected
    assert device.received == [[{"type": "authorization", "data": TOKEN}]]
    await ws.close()


@pytest.fixture(name="http_status")
def http_status_fixture(
    api: HomeWizardEnergyV2, monkeypatch: pytest.MonkeyPatch
) -> list[int]:
    """Let HTTP requests of the API client fail with 401, and count them."""
    requests: list[int] = []

    async def request(path: str, *_args, **_kwargs):
        assert path == "/api"
        requests.append(401)
        raise UnauthorizedError("Token rejected")

    monkeypatch.setattr(api, "_request", request)
    return requests


@pytest.mark.parametrize(
    ("unauthorized", "http_requests"),
    [
        # Device drops the connection, as a P1 Meter does
        (None, 1),
        ({"type": "error", "data": {"message": "user:unauthorized"}}, 0),
    ],
)
async def test_connect_rejected_token(
    device: FakeDevice,
    api: HomeWizardEnergyV2,
    http_status: list[int],
    unauthorized: dict[str, Any] | None,
    http_requests: int,
):
    """Test a token that is rejected by the device."""
    device.unauthorized = unauthorized
    api._token = "invalid"  # pylint: disable=protected-access
    states: list[bool] = []
    ws = api.websocket(on_connection_change=states.append)

    with pytest.raises(UnauthorizedError, match="Token rejected"):
        await ws.connect()

    assert not ws.connected
    assert not states
    assert len(http_status) == http_requests
    # The session of the WebSocket is closed, without calling close()
    assert ws._session is None  # pylint: disable=protected-access
    assert device.attempts == 1


@pytest.mark.usefixtures("http_status")
async def test_connect_rejected_token_in_stream(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that a rejected token is raised with reconnect, instead of retried."""
    api._token = "invalid"  # pylint: disable=protected-access
    ws = api.websocket()

    with pytest.raises(UnauthorizedError):
        async for _ in ws.events(reconnect=True):
            pass

    assert device.attempts == 1


@pytest.mark.parametrize("http_error", [None, RequestError("Device is offline")])
async def test_connect_lost_during_authorization(
    device: FakeDevice,
    api: HomeWizardEnergyV2,
    monkeypatch: pytest.MonkeyPatch,
    http_error: Exception | None,
):
    """Test a connection that is lost after sending the token, while the token is fine."""
    requests = 0

    async def request(*_args, **_kwargs):
        nonlocal requests
        requests += 1
        if http_error is not None:
            raise http_error
        return 200, "{}"

    monkeypatch.setattr(api, "_request", request)
    api._token = "valid-but-connection-drops"  # pylint: disable=protected-access
    ws = api.websocket()

    # The token is not rejected via HTTP, so connecting again may succeed
    with pytest.raises(WebSocketDisconnectedError):
        await ws.connect()

    assert requests == 1
    assert not ws.connected
    assert device.attempts == 1


async def test_connect_unsupported_device(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test a device that has the v2 API, but no WebSocket."""
    # pylint: disable-next=protected-access
    api._device = Device.from_dict(json.loads(load_fixtures("HWE-SKT/device.json")))
    ws = api.websocket()

    with pytest.raises(UnsupportedError, match="Device has no WebSocket"):
        await ws.connect()

    with pytest.raises(UnsupportedError):
        async for _ in ws.events(reconnect=True):
            pass

    assert not ws.connected
    # Device is not bothered with a connection
    assert device.attempts == 0


async def test_connect_gets_device_information(
    device: FakeDevice, api: HomeWizardEnergyV2, monkeypatch: pytest.MonkeyPatch
):
    """Test that the device information is requested when it is not known yet."""
    known_device = api._device  # pylint: disable=protected-access
    api._device = None  # pylint: disable=protected-access
    requests = 0

    async def request(*_args, **_kwargs):
        nonlocal requests
        requests += 1
        if requests == 1:
            raise RequestError("Device is offline")
        return 200, json.dumps(TOPICS["device"])

    monkeypatch.setattr(api, "_request", request)
    ws = api.websocket()

    # Device can't be reached, connecting again may succeed
    with pytest.raises(WebSocketDisconnectedError, match="device information"):
        await ws.connect()
    assert device.attempts == 0

    await ws.connect()

    assert ws.connected
    assert api._device == known_device  # pylint: disable=protected-access
    await ws.close()


async def test_context_manager_closes_on_error(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that nothing is left open when connecting with the context manager fails."""
    device.status = 503
    ws = api.websocket()

    with pytest.raises(WebSocketDisconnectedError):
        async with ws:
            pytest.fail("Should not connect")

    assert ws._session is None  # pylint: disable=protected-access
    assert [message async for message in ws.events(reconnect=True)] == []
    assert device.attempts == 1


@pytest.mark.parametrize(
    ("greeting", "authorized", "error"),
    [
        ({"type": "authorized"}, {"type": "authorized"}, "authorization request"),
        (AUTHORIZATION_REQUESTED, {"type": "device"}, "Expected to be authorized"),
        (
            AUTHORIZATION_REQUESTED,
            {"type": "error", "data": {"message": "request:internal-server-error"}},
            "request:internal-server-error",
        ),
        (AUTHORIZATION_REQUESTED, {"type": "error"}, "Unknown error"),
    ],
)
async def test_connect_unexpected_flow(
    device: FakeDevice,
    api: HomeWizardEnergyV2,
    greeting: dict[str, Any],
    authorized: dict[str, Any],
    error: str,
):
    """Test a device that does not follow the authorization flow."""
    device.greeting = greeting
    device.authorized = authorized
    ws = api.websocket()

    with pytest.raises(RequestError, match=error) as ex:
        await ws.connect()

    # This will not go away by connecting again
    assert not isinstance(ex.value, WebSocketDisconnectedError)
    assert not ws.connected
    await ws.close()


async def test_connect_no_authorization_request(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test a device that never asks for authorization."""
    api._request_timeout = 0.05  # pylint: disable=protected-access
    device.greeting = None
    ws = api.websocket()

    with pytest.raises(WebSocketDisconnectedError):
        await ws.connect()

    assert not ws.connected
    await ws.close()


@pytest.mark.parametrize(
    ("status", "error"),
    [
        # Energy Socket with v2 API, but without WebSocket
        (400, UnsupportedError),
        (404, UnsupportedError),
        (401, UnauthorizedError),
        (500, WebSocketDisconnectedError),
    ],
)
async def test_connect_refused(
    device: FakeDevice, api: HomeWizardEnergyV2, status: int, error: type[Exception]
):
    """Test a device that does not accept the WebSocket connection."""
    device.status = status
    ws = api.websocket()

    with pytest.raises(error):
        await ws.connect()

    assert not ws.connected
    await ws.close()


async def test_connect_unreachable(
    api: HomeWizardEnergyV2, monkeypatch: pytest.MonkeyPatch
):
    """Test a device that can't be reached."""

    async def ws_connect(*_args, **_kwargs):
        raise ClientConnectionError

    monkeypatch.setattr(ClientSession, "ws_connect", ws_connect)
    ws = api.websocket()

    with pytest.raises(WebSocketDisconnectedError, match="Unable to connect"):
        await ws.connect()

    await ws.close()


async def test_commands(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test the messages that are sent for each command."""
    async with api.websocket() as ws:
        await ws.subscribe(WebSocketTopic.MEASUREMENT)
        await ws.subscribe("system")
        await ws.unsubscribe(WebSocketTopic.MEASUREMENT)
        await ws.identify()
        await ws.request(WebSocketTopic.DEVICE)
        await ws.send("system", {"cloud_enabled": False})

        # Wait until the device has seen all messages
        async for message in ws.events():
            if message["type"] == "error":
                break

    assert device.received == [
        [
            {"type": "authorization", "data": TOKEN},
            {"type": "subscribe", "data": "measurement"},
            {"type": "subscribe", "data": "system"},
            {"type": "unsubscribe", "data": "measurement"},
            {"type": "identify"},
            {"type": "device"},
            {"type": "system", "data": {"cloud_enabled": False}},
        ]
    ]


async def test_commands_connect_when_needed(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that commands connect first."""
    ws = api.websocket()

    # Not connected, so nothing to unsubscribe from
    await ws.unsubscribe(WebSocketTopic.SYSTEM)
    assert device.attempts == 0

    await ws.subscribe(WebSocketTopic.MEASUREMENT)
    assert ws.connected
    assert await ws.receive() == {"type": "measurement", "data": TOPICS["measurement"]}

    await ws.close()
    await ws.identify()
    assert ws.connected

    # The subscription is restored
    assert await ws.receive() == {"type": "measurement", "data": TOPICS["measurement"]}
    assert device.received[1] == [
        {"type": "authorization", "data": TOKEN},
        {"type": "subscribe", "data": "measurement"},
        {"type": "identify"},
    ]
    await ws.close()


async def test_events(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test receiving messages as received."""
    async with api.websocket() as ws:
        await ws.subscribe(WebSocketTopic.MEASUREMENT)

        messages = []
        async for message in ws.events():
            messages.append(message)
            if len(messages) == 2:
                break
            # Device sends an update
            await device.connection.send_json({"type": "measurement", "data": {}})

    assert messages == [
        {"type": "measurement", "data": TOPICS["measurement"]},
        {"type": "measurement", "data": {}},
    ]


async def test_events_typed(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test receiving messages as events."""
    async with api.websocket() as ws:
        await ws.subscribe(WebSocketTopic.ALL)

        events = []
        async for event in ws.events_typed():
            events.append(event)
            if len(events) == len(TOPICS):
                break

    assert [type(event) for event in events] == [
        DeviceEvent,
        MeasurementEvent,
        SystemEvent,
        BatteriesEvent,
        HomeWizardEnergyWebSocketEvent,
    ]
    assert [event.type for event in events] == list(TOPICS)
    assert [event.raw["data"] for event in events] == list(TOPICS.values())

    # pylint: disable-next=unbalanced-tuple-unpacking
    device_event, measurement, system, batteries, user = events
    assert device_event.data == Device.from_dict(TOPICS["device"])
    assert measurement.data == Measurement.from_dict(TOPICS["measurement"])
    assert measurement.data.power_w == TOPICS["measurement"]["power_w"]
    assert system.data == System.from_dict(TOPICS["system"])
    assert batteries.data == Batteries.from_dict(TOPICS["batteries"])
    assert user.data == TOPICS["user"]
    assert device.attempts == 1


async def test_receive_typed(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test receiving a single event."""
    async with api.websocket() as ws:
        await ws.request(WebSocketTopic.SYSTEM)

        event = await ws.receive_typed()

    assert isinstance(event, SystemEvent)
    assert event.data.wifi_ssid == TOPICS["system"]["wifi_ssid"]
    assert device.attempts == 1


async def test_events_typed_undecodable(
    device: FakeDevice, api: HomeWizardEnergyV2, caplog: pytest.LogCaptureFixture
):
    """Test a message of a known topic that does not fit the model."""
    async with api.websocket() as ws:
        await device.connection.send_json({"type": "device", "data": {"a": 1}})
        await device.connection.send_json({"type": "measurement", "data": "text"})

        with caplog.at_level(logging.WARNING):
            first = await ws.receive_typed()
            second = await ws.receive_typed()

    # pylint: disable=unidiomatic-typecheck
    assert type(first) is HomeWizardEnergyWebSocketEvent
    assert first.data == {"a": 1}
    assert "Failed to decode WebSocket message of type 'device'" in caplog.text
    assert type(second) is HomeWizardEnergyWebSocketEvent
    assert second.data == "text"


async def test_events_error_does_not_end_stream(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that an error of the device is an event, and the stream continues."""
    async with api.websocket() as ws:
        await ws.subscribe("bogus")
        await ws.subscribe(WebSocketTopic.MEASUREMENT)

        events = []
        async for event in ws.events_typed(reconnect=True):
            events.append(event)
            if len(events) == 2:
                break

    assert isinstance(events[0], ErrorEvent)
    assert events[0].message == "request:unknown-subscription"
    assert isinstance(events[1], MeasurementEvent)
    assert device.attempts == 1


async def test_events_ignores_invalid_messages(
    device: FakeDevice, api: HomeWizardEnergyV2, caplog: pytest.LogCaptureFixture
):
    """Test that messages that are not a JSON object are skipped."""
    async with api.websocket() as ws:
        await device.connection.send_str("not json")
        await device.connection.send_str('["a list"]')
        await device.connection.send_bytes(b"binary")
        await ws.request(WebSocketTopic.SYSTEM)

        with caplog.at_level(logging.WARNING):
            async for message in ws.events():
                assert message["type"] == "system"
                break

    assert caplog.text.count("Ignoring WebSocket message") == 3
    assert device.attempts == 1


@pytest.mark.parametrize(
    ("send", "error"),
    [
        (lambda ws: ws.send_str("not json"), "not valid JSON"),
        (lambda ws: ws.send_str("1"), "not a JSON object"),
        (lambda ws: ws.send_bytes(b"binary"), "Unexpected WebSocket message type"),
    ],
)
async def test_receive_invalid_message(
    device: FakeDevice, api: HomeWizardEnergyV2, send, error: str
):
    """Test receiving a single message that is not a JSON object."""
    async with api.websocket() as ws:
        await send(device.connection)

        with pytest.raises(ResponseError, match=error):
            await ws.receive()

        # The connection is kept
        assert ws.connected


async def test_receive_not_connected(api: HomeWizardEnergyV2):
    """Test receiving without connection."""
    ws = api.websocket()

    with pytest.raises(WebSocketDisconnectedError, match="not connected"):
        await ws.receive()


async def test_receive_connection_lost(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test receiving while the device closes the connection."""
    states: list[bool] = []
    ws = api.websocket(on_connection_change=states.append)
    await ws.connect()

    await device.connection.close()
    with pytest.raises(WebSocketDisconnectedError, match="closed"):
        await ws.receive()

    assert not ws.connected
    assert states == [True, False]

    await ws.close()


async def test_events_reconnect_restores_subscriptions(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that the subscriptions are sent again after a reconnect."""
    states: list[bool] = []
    ws = api.websocket(on_connection_change=states.append)
    await ws.subscribe(WebSocketTopic.MEASUREMENT)
    await ws.subscribe(WebSocketTopic.SYSTEM)
    await ws.subscribe(WebSocketTopic.DEVICE)
    await ws.unsubscribe(WebSocketTopic.DEVICE)

    events = []
    async for event in ws.events_typed(reconnect=True):
        events.append(event)
        if len(events) == 3:
            # Device drops the connection, for example because it restarts
            await device.connection.close()
        if len(events) == 5:
            break

    assert [type(event) for event in events] == [
        MeasurementEvent,
        SystemEvent,
        DeviceEvent,
        MeasurementEvent,
        SystemEvent,
    ]
    assert device.received[1] == [
        {"type": "authorization", "data": TOKEN},
        {"type": "subscribe", "data": "measurement"},
        {"type": "subscribe", "data": "system"},
    ]
    assert states == [True, False, True]

    await ws.close()
    assert states == [True, False, True, False]


async def test_events_reconnect_while_unreachable(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that connecting is tried again until the device is back."""
    device.status = 503
    ws = api.websocket()

    async def restore_device():
        await device.wait_for(attempts=3)
        device.status = None

    task = asyncio.create_task(restore_device())
    ws._subscriptions.add("measurement")  # pylint: disable=protected-access

    async with asyncio.timeout(5):
        async for message in ws.events(reconnect=True):
            assert message["type"] == "measurement"
            break

    await task
    assert device.attempts >= 4
    await ws.close()


async def test_events_without_reconnect(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test that a lost connection is raised without reconnect."""
    async with api.websocket() as ws:
        await ws.subscribe(WebSocketTopic.MEASUREMENT)

        with pytest.raises(WebSocketDisconnectedError):
            async for _ in ws.events():
                await device.connection.close()

        assert not ws.connected

    assert device.attempts == 1


@pytest.mark.parametrize(
    ("status", "error"),
    [(400, UnsupportedError), (404, UnsupportedError), (401, UnauthorizedError)],
)
async def test_events_reconnect_stops_on_permanent_error(
    device: FakeDevice, api: HomeWizardEnergyV2, status: int, error: type[Exception]
):
    """Test that an error that will not go away is raised, also with reconnect."""
    async with api.websocket() as ws:
        await ws.subscribe(WebSocketTopic.MEASUREMENT)

        with pytest.raises(error):
            async for _ in ws.events(reconnect=True):
                # For example a firmware without WebSocket, or a removed user
                device.status = status
                await device.connection.close()

    assert device.attempts == 2


async def test_close_ends_events(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test that closing ends the stream, without connecting again."""
    ws = api.websocket()
    await ws.subscribe(WebSocketTopic.MEASUREMENT)
    received = asyncio.Event()

    async def consume() -> int:
        count = 0
        async for _ in ws.events(reconnect=True):
            count += 1
            received.set()
        return count

    task = asyncio.create_task(consume())
    await received.wait()

    await ws.close()

    async with asyncio.timeout(1):
        assert await task == 1
    assert not ws.connected
    assert device.attempts == 1

    # A closed WebSocket yields nothing
    assert [message async for message in ws.events(reconnect=True)] == []
    assert device.attempts == 1


async def test_close_ends_events_typed(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test that closing ends the stream of events."""
    ws = api.websocket()
    await ws.subscribe(WebSocketTopic.MEASUREMENT)

    events = []
    async for event in ws.events_typed(reconnect=True):
        events.append(event)
        await ws.close()

    assert len(events) == 1
    assert device.attempts == 1


async def test_send_not_connected():
    """Test sending over a connection that is gone."""
    with pytest.raises(WebSocketDisconnectedError, match="not connected"):
        # pylint: disable-next=protected-access
        await HomeWizardEnergyWebSocket._send(None, "identify")


async def test_close_ends_events_while_reconnecting(
    device: FakeDevice, api: HomeWizardEnergyV2, monkeypatch: pytest.MonkeyPatch
):
    """Test that closing ends the stream while waiting to connect again."""
    monkeypatch.setattr(websocket_module, "MAX_RECONNECT_BACKOFF", 30)
    device.status = 503
    ws = api.websocket()

    async def consume() -> list[dict[str, Any]]:
        return [message async for message in ws.events(reconnect=True)]

    task = asyncio.create_task(consume())
    await device.wait_for(attempts=1)
    await asyncio.sleep(0.05)

    await ws.close()

    async with asyncio.timeout(1):
        assert await task == []
    assert device.attempts == 1


async def test_close_while_events_starts_connecting(
    device: FakeDevice, api: HomeWizardEnergyV2
):
    """Test that the stream does not connect when closed in the meantime."""
    ws = api.websocket()

    async def consume() -> list[dict[str, Any]]:
        return [message async for message in ws.events(reconnect=True)]

    async with ws._lock:  # pylint: disable=protected-access
        task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        closing = asyncio.create_task(ws.close())
        await asyncio.sleep(0.01)

    async with asyncio.timeout(1):
        assert await task == []
        await closing
    assert device.attempts == 0


async def test_own_session(device: FakeDevice, api: HomeWizardEnergyV2):
    """Test that the WebSocket does not take the only connection of the API client."""
    # pylint: disable=protected-access
    await api._create_clientsession()
    ws = api.websocket()

    await ws.connect()

    session = ws._session
    assert session is not None
    assert session is not api._session

    await ws.close()

    assert session.closed
    assert not api._session.closed
    assert device.attempts == 1


async def test_provided_session(device: FakeDevice):
    """Test that the session that was passed to the API client is used."""
    # pylint: disable=protected-access
    async with ClientSession() as session:
        api = HomeWizardEnergyV2("example.com", token=TOKEN, clientsession=session)
        api._device = Device.from_dict(TOPICS["device"])
        ws = api.websocket()

        await ws.connect()

        assert ws.connected
        assert ws._session is None

        await ws.close()
        assert not session.closed

    with pytest.raises(RequestError, match="Client session is closed") as ex:
        await ws.connect()

    assert not isinstance(ex.value, WebSocketDisconnectedError)
    assert device.attempts == 1


async def test_send_failure(
    device: FakeDevice, api: HomeWizardEnergyV2, monkeypatch: pytest.MonkeyPatch
):
    """Test a connection that breaks while sending."""
    async with api.websocket() as ws:

        async def send_json(*_args, **_kwargs):
            raise ConnectionResetError

        monkeypatch.setattr(ws._ws, "send_json", send_json)  # pylint: disable=protected-access

        with pytest.raises(WebSocketDisconnectedError, match="Failed to send"):
            await ws.identify()

    assert device.attempts == 1


async def test_connection_error_frame(
    device: FakeDevice, api: HomeWizardEnergyV2, monkeypatch: pytest.MonkeyPatch
):
    """Test a connection that fails, for example when the device stops answering pings."""
    async with api.websocket() as ws:

        async def receive(*_args, **_kwargs):
            return type("Message", (), {"type": WSMsgType.ERROR, "data": "timeout"})

        monkeypatch.setattr(ws._ws, "receive", receive)  # pylint: disable=protected-access

        with pytest.raises(WebSocketDisconnectedError, match="connection failed"):
            await ws.receive()

        assert not ws.connected

    assert device.attempts == 1


async def test_connection_change_callback_error(
    device: FakeDevice, api: HomeWizardEnergyV2, caplog: pytest.LogCaptureFixture
):
    """Test that an error in the callback does not break the connection."""

    def on_connection_change(_connected: bool) -> None:
        raise ValueError("Oops")

    async with api.websocket(on_connection_change=on_connection_change) as ws:
        assert ws.connected

    assert "Error in WebSocket connection change callback" in caplog.text
    assert device.attempts == 1
