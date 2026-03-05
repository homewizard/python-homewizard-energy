"""Test websocket support for HomeWizard Energy v2."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp import WSMsgType

from homewizard_energy.errors import RequestError, UnauthorizedError
from homewizard_energy.models import Measurement
from homewizard_energy.v2.websocket import (
    HomeWizardEnergyWebSocket,
    HomeWizardEnergyWebSocketEvent,
    WebSocketTopic,
)

pytestmark = [pytest.mark.asyncio]


def ws_msg(payload: dict) -> SimpleNamespace:
    """Create a text websocket message."""
    return SimpleNamespace(type=WSMsgType.TEXT, data=json.dumps(payload))


class FakeWebSocket:
    """Minimal websocket test double."""

    def __init__(self, messages: list[SimpleNamespace]):
        self._messages = messages
        self.closed = False
        self.sent: list[dict] = []

    async def receive(self, timeout=None):
        """Return the next mocked websocket message."""
        _ = timeout
        if not self._messages:
            self.closed = True
            return SimpleNamespace(type=WSMsgType.CLOSED, data=None)

        msg = self._messages.pop(0)
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
            self.closed = True
        return msg

    async def send_json(self, payload: dict):
        """Capture payloads sent by the client."""
        self.sent.append(payload)

    async def close(self):
        """Mark websocket as closed."""
        self.closed = True


async def test_connect_requires_token():
    """Test websocket connect requires token."""
    client = HomeWizardEnergyWebSocket("example.com", token=None)

    with pytest.raises(UnauthorizedError):
        await client.connect()


async def test_connect_authenticates_with_token():
    """Test websocket authentication handshake."""
    ws = FakeWebSocket(
        [
            ws_msg(
                {"type": "authorization_requested", "data": {"api_version": "2.0.0"}}
            ),
            ws_msg({"type": "authorized"}),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(return_value=ws)

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    await client.connect()

    assert ws.sent == [{"type": "authorization", "data": "secret"}]


async def test_connect_fails_when_authorization_not_requested():
    """Test websocket fails when first message is unexpected."""
    ws = FakeWebSocket([ws_msg({"type": "authorized"})])

    session = AsyncMock()
    session.ws_connect = AsyncMock(return_value=ws)

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    with pytest.raises(RequestError, match="authorization was not requested"):
        await client.connect()

    assert ws.closed is True
    assert client._ws is None  # pylint: disable=protected-access


async def test_send_helpers_write_expected_payloads():
    """Test helper methods map to expected websocket commands."""
    ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(return_value=ws)

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    await client.connect()
    await client.subscribe(WebSocketTopic.MEASUREMENT)
    await client.unsubscribe(WebSocketTopic.MEASUREMENT)
    await client.identify()
    await client.request(WebSocketTopic.SYSTEM)

    assert ws.sent == [
        {"type": "authorization", "data": "secret"},
        {"type": "subscribe", "data": "measurement"},
        {"type": "unsubscribe", "data": "measurement"},
        {"type": "identify"},
        {"type": "system"},
    ]


async def test_receive_raises_on_error_message():
    """Test websocket type=error raises request error."""
    ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
            ws_msg(
                {
                    "type": "error",
                    "data": {
                        "message": "json:parameter-invalid-type:status_led_brightness_pct"
                    },
                }
            ),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(return_value=ws)

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    await client.connect()

    with pytest.raises(RequestError, match="json:parameter-invalid-type"):
        await client.receive()


async def test_receive_raises_on_invalid_json_shape():
    """Test websocket non-object JSON payload raises request error."""
    ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
            SimpleNamespace(type=WSMsgType.TEXT, data='["not", "an", "object"]'),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(return_value=ws)

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    await client.connect()

    with pytest.raises(RequestError, match="payload shape"):
        await client.receive()


async def test_receive_typed_decodes_measurement_payload():
    """Test typed receive decodes known topic payloads to models."""
    ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
            ws_msg({"type": "measurement", "data": {"power_w": 123.4}}),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(return_value=ws)

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    await client.connect()
    event = await client.receive_typed()

    assert isinstance(event, HomeWizardEnergyWebSocketEvent)
    assert event.type == "measurement"
    assert isinstance(event.data, Measurement)
    assert event.data.power_w == 123.4


async def test_events_reconnects_when_connection_closes(monkeypatch):
    """Test events iterator reconnects with backoff on dropped socket."""
    first_ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
            SimpleNamespace(type=WSMsgType.CLOSED, data=None),
        ]
    )
    second_ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
            ws_msg({"type": "measurement", "data": {"power_w": 123.4}}),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(side_effect=[first_ws, second_ws])

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    sleep_mock = AsyncMock()
    monkeypatch.setattr("homewizard_energy.v2.websocket.asyncio.sleep", sleep_mock)

    events = client.events(reconnect=True)
    event = await anext(events)

    assert event == {"type": "measurement", "data": {"power_w": 123.4}}
    assert session.ws_connect.call_count == 2
    sleep_mock.assert_awaited()


async def test_events_reconnects_when_connect_fails_transiently(monkeypatch):
    """Test events iterator reconnects when connect fails before succeeding."""
    second_ws = FakeWebSocket(
        [
            ws_msg({"type": "authorization_requested"}),
            ws_msg({"type": "authorized"}),
            ws_msg({"type": "measurement", "data": {"power_w": 123.4}}),
        ]
    )

    session = AsyncMock()
    session.ws_connect = AsyncMock(side_effect=[Exception("connect failed"), second_ws])

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )
    client._get_ssl_context = AsyncMock(return_value=False)  # pylint: disable=protected-access

    sleep_mock = AsyncMock()
    monkeypatch.setattr("homewizard_energy.v2.websocket.asyncio.sleep", sleep_mock)

    events = client.events(reconnect=True)
    event = await anext(events)

    assert event == {"type": "measurement", "data": {"power_w": 123.4}}
    assert session.ws_connect.call_count == 2
    sleep_mock.assert_awaited()


async def test_events_does_not_reconnect_on_closed_external_session():
    """Test reconnect is disabled when externally owned session is closed."""
    session = AsyncMock()
    session.closed = True

    client = HomeWizardEnergyWebSocket(
        "example.com", token="secret", clientsession=session
    )

    events = client.events(reconnect=True)

    with pytest.raises(RequestError, match="session is closed"):
        await anext(events)


# pylint: disable=protected-access
async def test_is_transient_error_matches_receive_failures():
    """Test reconnect classifier matches common transient websocket errors."""
    assert HomeWizardEnergyWebSocket._is_transient_error(
        RequestError("WebSocket receive failed")
    )
    assert HomeWizardEnergyWebSocket._is_transient_error(
        RequestError("Connection reset by peer")
    )
    assert not HomeWizardEnergyWebSocket._is_transient_error(
        RequestError("json:parameter-invalid-type")
    )
