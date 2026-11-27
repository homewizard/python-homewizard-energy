# HomeWizard Energy: `python-homewizard-energy`

Asyncio package to communicate with HomeWizard Energy devices
This package is aimed at basic control of the device. Initial setup and configuration is assumed to done with the official HomeWizard Energy app.

[![Testing](https://github.com/homewizard/python-homewizard-energy/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/homewizard/python-homewizard-energy/actions/workflows/tests.yaml)
[![Codecov](https://img.shields.io/codecov/c/github/homewizard/python-homewizard-energy)](https://app.codecov.io/gh/homewizard/python-homewizard-energy)
[![Release](https://img.shields.io/github/v/release/homewizard/python-homewizard-energy)](https://github.com/homewizard/python-homewizard-energy/releases)


# Usage
Instantiate the HomeWizard class and access the API.

For more details on the API see the API documentation for HomeWizard Energy on https://api-documentation.homewizard.com

## Installation
```bash
python3 -m pip install python-homewizard-energy
```

## Example

### API v1
```python
import asyncio
from homewizard_energy import HomeWizardEnergyV1

IP_ADDRESS = "192.168.1.123"


async def main():

    async with HomeWizardEnergyV1(host=IP_ADDRESS) as api:

        # Get device information, like firmware version
        print(await api.device())

        # Get measurements, like energy or water usage
        measurement = await api.measurement()
        print(measurement.energy_import_kwh)

        # Example of getting raw telegram data
        telegram = await api.telegram()
        print(telegram)  # Raw P1 meter data

        # Get all data and remap v1 data to new v2 structure
        print(await api.combined())

        # Turn on the Energy Socket outlet (works with both v1 and v2 API)
        await api.system(power_on=True)


asyncio.run(main())
```

### API v2 WebSocket (real-time updates)
The WebSocket is available on devices that [support it](https://api-documentation.homewizard.com/docs/v2/websocket). Check this with `(await api.device()).supports_websocket()`.

```python
import asyncio
from homewizard_energy import (
    ErrorEvent,
    HomeWizardEnergyV2,
    MeasurementEvent,
    WebSocketTopic,
)

IP_ADDRESS = "192.168.1.123"
TOKEN = "your-token"


async def main():
    async with HomeWizardEnergyV2(host=IP_ADDRESS, token=TOKEN) as api:
        async with api.websocket as ws:
            await ws.subscribe(WebSocketTopic.MEASUREMENT)

            # With `reconnect=True`, the connection and the subscriptions are
            # restored when the connection is lost
            async for event in ws.events_typed(reconnect=True):
                if isinstance(event, MeasurementEvent):
                    print(event.data.power_w)
                elif isinstance(event, ErrorEvent):
                    print(f"Device reported an error: {event.message}")


asyncio.run(main())
```

Known topics are received as `DeviceEvent`, `MeasurementEvent`, `SystemEvent` or `BatteriesEvent`, with the same models as the HTTP API. If you prefer the messages as received, use `ws.events()` or `ws.receive()`.

Instead of iterating, you can pass a callback when you subscribe. Messages are then received in the background, and the connection is restored when it is lost:

```python
def on_measurement(event: MeasurementEvent) -> None:
    print(event.data.power_w)


async def main():
    async with HomeWizardEnergyV2(host=IP_ADDRESS, token=TOKEN) as api:
        unsubscribe = await api.websocket.subscribe(
            WebSocketTopic.MEASUREMENT, on_measurement
        )

        await asyncio.sleep(60)

        # Stop calling the callback
        unsubscribe()
```

The callback may also be a coroutine function. Use either callbacks or iteration. Using both at the same time raises a `RuntimeError`.

Good to know:
- `api.websocket` always returns the same WebSocket client. It is closed together with the API client.
- The stream ends, and callbacks stop, when you call `ws.close()`.
- A rejected token raises `UnauthorizedError`, and a device without WebSocket raises `UnsupportedError`. These are also raised with `reconnect=True`. A lost connection raises `WebSocketDisconnectedError`, unless you use `reconnect=True`.
- With callbacks, there is nothing to raise an error to. Use `ws.on_error(callback)` to get the error when receiving stops, for example an `UnauthorizedError` for a token that was removed. A lost connection is restored and is not reported there.
- To follow the connection state, use `ws.on_connection_change(callback)`. The callback is called with `True` or `False`.
- The WebSocket keeps one connection to the device open, next to the connection for HTTP requests.

# Development and contribution
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Requirements
- Python 3.12 or higher
- [Poetry](https://python-poetry.org/docs/#installing-with-pipx)

## Installation and setup
```bash
poetry install
poetry shell
pre-commit install
```

You can now start developing. The pre-commit hooks will run automatically when you commit your changes. Please note that a failed pre-commit hook will prevent you from committing your changes. This is to make sure that the code is formatted correctly and that the tests pass.
