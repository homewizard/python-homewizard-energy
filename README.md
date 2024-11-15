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
```python
import asyncio
from homewizard_energy import HomeWizardEnergyV1V1

IP_ADDRESS = "192.168.1.123"


async def main():

    async with HomeWizardEnergyV1(host=IP_ADDRESS) as api:

         # Get device information, like firmware version
        print(await api.device())

         # Get measurements, like energy or water usage
        data = await api.data()
        print(data.total_energy_import_kwh)

         # Turn on the Energy Socket outlet
        await api.state_set(power_on=True)


asyncio.run(main())
```

# Development and contribution
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Requirements
- Python 3.10 or higher
- [Poetry](https://python-poetry.org/docs/#installing-with-pipx)

## Installation and setup
```bash
poetry install
poetry shell
pre-commit install
```

You can now start developing. The pre-commit hooks will run automatically when you commit your changes. Please note that a failed pre-commit hook will prevent you from committing your changes. This is to make sure that the code is formatted correctly and that the tests pass.
