"""Tests that HomeWizardEnergyV1 sends at most one request at a time."""

import asyncio
from contextlib import asynccontextmanager

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from homewizard_energy import HomeWizardEnergyV1

from . import load_fixtures

pytestmark = [pytest.mark.asyncio]

ROUTES = {
    "/api": "HWE-SKT/device.json",
    "/api/v1/data": "HWE-SKT/data.json",
    "/api/v1/system": "HWE-SKT/system.json",
    "/api/v1/state": "HWE-SKT/state_all.json",
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
            fail_once: Paths that answer the first request with HTTP 500.
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
            if request.path in self.fail_once:
                self.fail_once.remove(request.path)
                self.events.append(f"fail {request.path}")
                return web.Response(status=500)
            body = load_fixtures(ROUTES[request.path]).encode()
            resp = web.StreamResponse(headers={"Content-Type": "application/json"})
            resp.content_length = len(body)
            await resp.prepare(request)
            await resp.write(body[: len(body) // 2])
            await asyncio.sleep(self.body_delay)
            await resp.write(body[len(body) // 2 :])
            await resp.write_eof()
            self.events.append(f"end {request.path}")
            return resp
        finally:
            self.in_flight -= 1


@asynccontextmanager
async def serve(device: FakeDevice):
    """Run the fake device on localhost and yield its host:port."""
    app = web.Application()
    for path in ROUTES:
        app.router.add_route("*", path, device.handle)
    server = TestServer(app, host="127.0.0.1")
    await server.start_server()
    try:
        yield f"127.0.0.1:{server.port}"
    finally:
        await server.close()


async def test_concurrent_calls_use_one_connection():
    """Concurrent combined() and other calls never overlap on the device."""
    device = FakeDevice(delay=0.02, body_delay=0.02)

    async with serve(device) as host, aiohttp.ClientSession() as session:
        # Shared session without a per-host limit, like Home Assistant's
        api = HomeWizardEnergyV1(host, clientsession=session)

        results = await asyncio.gather(
            api.combined(),
            api.combined(),
            api.measurement(),
            api.state(),
            api.system(),
        )

    assert all(result is not None for result in results)
    assert results[0].measurement is not None
    assert results[0].state is not None
    assert results[0].system is not None
    # 2x combined() (device, data, system, state) + 3 single calls
    assert len([event for event in device.events if event.startswith("start")]) == 11
    assert device.max_in_flight == 1
    assert len(device.peers) == 1


async def test_body_is_read_before_next_request():
    """The next request only starts after the previous body is fully read."""
    device = FakeDevice(body_delay=0.1)

    async with serve(device) as host, aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1(host, clientsession=session)

        await asyncio.gather(api.measurement(), api.state())

    assert device.events in (
        [
            "start /api/v1/data",
            "end /api/v1/data",
            "start /api/v1/state",
            "end /api/v1/state",
        ],
        [
            "start /api/v1/state",
            "end /api/v1/state",
            "start /api/v1/data",
            "end /api/v1/data",
        ],
    )
    assert device.max_in_flight == 1
    assert len(device.peers) == 1


async def test_lock_wait_does_not_count_towards_timeout():
    """A request queued longer than the timeout succeeds without retries."""
    device = FakeDevice(delay=0.3)

    async with serve(device) as host, aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1(host, clientsession=session, timeout=0.5)

        # The last request waits ~0.6s for the lock, longer than the timeout,
        # but its own request only takes ~0.3s.
        await asyncio.gather(api.measurement(), api.state(), api.system())

    assert device.events.count("start /api/v1/data") == 1
    assert device.events.count("start /api/v1/state") == 1
    assert device.events.count("start /api/v1/system") == 1
    assert device.max_in_flight == 1


async def test_retry_releases_lock_during_backoff():
    """A queued request runs while a failed request waits for its retry."""
    device = FakeDevice(fail_once=frozenset({"/api/v1/data"}))

    async with serve(device) as host, aiohttp.ClientSession() as session:
        api = HomeWizardEnergyV1(host, clientsession=session)

        measurement_task = asyncio.ensure_future(api.measurement())
        await asyncio.sleep(0)  # Let measurement() take the lock first
        await asyncio.gather(measurement_task, api.state())

    assert device.events == [
        "start /api/v1/data",
        "fail /api/v1/data",
        "start /api/v1/state",
        "end /api/v1/state",
        "start /api/v1/data",
        "end /api/v1/data",
    ]
