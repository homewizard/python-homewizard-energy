#!/usr/bin/env python3
"""Example for using Package."""

import argparse
import asyncio
import logging

from homewizard_energy import HomeWizardEnergy

parser = argparse.ArgumentParser(
    description="Example application for python-homewizard-energy."
)
parser.add_argument("host", help="Hostname or IP Address of the device")
parser.add_argument(
    "--loglevel",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default="DEBUG",
    help="Define loglevel, default is INFO.",
)

args = parser.parse_args()


async def main():
    """Run the example."""

    logging.basicConfig(level=args.loglevel)

    # Make contact with a energy device
    async with HomeWizardEnergy(args.host) as api:

        # Use the data
        print(await api.device())
        print(await api.data())
        print(await api.state())

        await api.state_set(power_on=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
