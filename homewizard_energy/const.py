"""Constants for HomeWizard Energy."""

import logging

LOGGER = logging.getLogger(__name__)

MODEL_TO_ID = {
    "HWE-P1": "p1dongle",
    "HWE-SKT": "energysocket",
    "HWE-WTR": "watermeter",
    "HWE-DSP": "display",
    "HWE-KWH1": "energymeter",
    "SDM230-wifi": "energymeter",
    "HWE-KWH3": "energymeter",
    "SDM630-wifi": "energymeter",
    "HWE-BAT": "battery",
}

MODEL_TO_NAME = {
    "HWE-P1": "Wi-Fi P1 Meter",
    "HWE-SKT": "Wi-Fi Energy Socket",
    "HWE-WTR": "Wi-Fi Watermeter",
    "HWE-KWH1": "Wi-Fi kWh Meter 1-phase",
    "HWE-KWH3": "Wi-Fi kWh Meter 3-phase",
    "SDM230-wifi": "Wi-Fi kWh Meter 1-phase",
    "SDM630-wifi": "Wi-Fi kWh Meter 3-phase",
    "HWE-BAT": "Plug-In Battery",
}
