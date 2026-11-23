"""Tests that HomeWizardEnergyV2 sends at most one request at a time."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import patch

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from homewizard_energy import HomeWizardEnergyV2

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]

ROUTES = {
    "/api": "HWE-P1/device.json",
    "/api/measurement": "HWE-P1/measurement_1_phase_no_gas.json",
    "/api/system": "HWE-P1/system.json",
    "/api/batteries": "HWE-P1/batteries.json",
}


class FakeDevice:
    """Device that records how requests and connections overlap."""

    def __init__(
        self,
        delay: float = 0.0,
        body_delay: float = 0.0,
        fail_once: frozenset[str] = frozenset(),
    ) -> None:
        """Initialize.

        Args:
            delay: Seconds to wait before sending the response headers.
            body_delay: Seconds to wait between the first and second half of
                the body, after the headers have been sent.
            fail_once: Paths that drop the connection halfway through the
                body on the first request.
        """
        self.delay = delay
        self.body_delay = body_delay
        self.fail_once = set(fail_once)
        self.in_flight = 0
        self.max_in_flight = 0
        self.peers: set[tuple] = set()
        self.events: list[str] = []

    async def handle(self, request: web.Request) -> web.StreamResponse:
        """Handle a request, streaming the body in two parts."""
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.peers.add(request.transport.get_extra_info("peername"))
        self.events.append(f"start {request.path}")
        try:
            await asyncio.sleep(self.delay)
            body = load_fixtures(ROUTES[request.path]).encode()
            resp = web.StreamResponse(headers={"Content-Type": "application/json"})
            resp.content_length = len(body)
            await resp.prepare(request)
            await resp.write(body[: len(body) // 2])
            if request.path in self.fail_once:
                self.fail_once.remove(request.path)
                self.events.append(f"fail {request.path}")
                request.transport.close()
                return resp
            await asyncio.sleep(self.body_delay)
            await resp.write(body[len(body) // 2 :])
            await resp.write_eof()
            self.events.append(f"end {request.path}")
            return resp
        finally:
            self.in_flight -= 1


@asynccontextmanager
async def serve(
    device: FakeDevice, timeout: float = 10
) -> AsyncIterator[HomeWizardEnergyV2]:
    """Run the fake device on localhost and yield an API client for it.

    The client uses a shared session without a per-host limit, like Home
    Assistant's. The fake device speaks plain HTTP, so HTTPS requests are
    sent to it over HTTP; TLS does not change how requests are serialized.
    """
    app = web.Application()
    for path in ROUTES:
        app.router.add_route("*", path, device.handle)
    server = TestServer(app, host="127.0.0.1")
    await server.start_server()

    async with aiohttp.ClientSession() as session:
        request = session.request

        def plain_http_request(method, url, **kwargs):
            kwargs.pop("ssl")
            kwargs.pop("server_hostname")
            return request(method, url.replace("https://", "http://", 1), **kwargs)

        with patch.object(session, "request", side_effect=plain_http_request):
            try:
                yield HomeWizardEnergyV2(
                    f"127.0.0.1:{server.port}",
                    token="token",
                    clientsession=session,
                    timeout=timeout,
                )
            finally:
                await server.close()


async def test_concurrent_calls_use_one_connection():
    """Concurrent combined() and other calls never overlap on the device."""
    device = FakeDevice(delay=0.02, body_delay=0.02)

    async with serve(device) as api:
        results = await asyncio.gather(
            api.combined(),
            api.combined(),
            api.measurement(),
            api.system(),
        )

    assert results[0].device is not None
    assert results[0].measurement is not None
    assert results[0].system is not None
    assert results[0].batteries is not None
    # 2x combined() (device, measurement, system, batteries) + 2 single calls
    assert len([event for event in device.events if event.startswith("start")]) == 10
    assert device.max_in_flight == 1
    assert len(device.peers) == 1


async def test_body_is_read_before_next_request():
    """The next request only starts after the previous body is fully read."""
    device = FakeDevice(body_delay=0.1)

    async with serve(device) as api:
        await asyncio.gather(api.measurement(), api.system())

    assert device.events in (
        [
            "start /api/measurement",
            "end /api/measurement",
            "start /api/system",
            "end /api/system",
        ],
        [
            "start /api/system",
            "end /api/system",
            "start /api/measurement",
            "end /api/measurement",
        ],
    )
    assert device.max_in_flight == 1
    assert len(device.peers) == 1


async def test_lock_wait_does_not_count_towards_timeout():
    """A request queued longer than the timeout succeeds without retries."""
    device = FakeDevice(delay=0.3)

    async with serve(device, timeout=0.5) as api:
        # The last request waits ~0.6s for the lock, longer than the timeout,
        # but its own request only takes ~0.3s.
        await asyncio.gather(api.measurement(), api.system(), api.batteries())

    assert device.events.count("start /api/measurement") == 1
    assert device.events.count("start /api/system") == 1
    assert device.events.count("start /api/batteries") == 1
    assert device.max_in_flight == 1


async def test_retry_releases_lock_during_backoff():
    """A queued request runs while a failed request waits for its retry."""
    device = FakeDevice(fail_once=frozenset({"/api/measurement"}))

    async with serve(device) as api:
        measurement_task = asyncio.ensure_future(api.measurement())
        await asyncio.sleep(0)  # Let measurement() take the lock first
        await asyncio.gather(measurement_task, api.system())

    assert device.events == [
        "start /api/measurement",
        "fail /api/measurement",
        "start /api/system",
        "end /api/system",
        "start /api/measurement",
        "end /api/measurement",
    ]
