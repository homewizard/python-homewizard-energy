# python-homewizard-energy

Asyncio package to communicate with HomeWizard Energy devices
This package is aimed at basic control of the device. Initial setup and configuration is assumed to done with the official HomeWizard Energy app.

## Disclaimer

This package is not developed, nor supported by HomeWizard.

## Installation
```bash
python3 -m pip install python-homewizard-energy
```

# Usage
Instantiate the HWEnergy class and access the API.

For more details on the API see the official API documentation on
https://homewizard-energy-api.readthedocs.io

# Example
The example below is available as a runnable script in the repository.

```python
from homewizard_energy import HomeWizardEnergy

# Make contact with a energy device
device = HomeWizardEnergy(args.host)

# Update device value
await device.update()

# Use the data
print(device.device.product_name)
print(device.device.serial)
print(device.data.wifi_ssid)

# Close connection
await device.close()
```
