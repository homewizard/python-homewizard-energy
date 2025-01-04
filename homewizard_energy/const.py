"""Constants for HomeWizard Energy."""

import logging
from enum import StrEnum

LOGGER = logging.getLogger(__name__)


class Model(StrEnum):
    """Model of the HomeWizard Energy device."""

    P1_METER = "HWE-P1"
    ENERGY_SOCKET = "HWE-SKT"
    WATER_METER = "HWE-WTR"
    DISPLAY = "HWE-DSP"
    ENERGY_METER_1_PHASE = "HWE-KWH1"
    ENERGY_METER_3_PHASE = "HWE-KWH3"
    ENERGY_METER_EASTRON_SDM230 = "SDM230-wifi"
    ENERGY_METER_EASTRON_SDM630 = "SDM630-wifi"
    BATTERY = "HWE-BAT"


MODEL_TO_ID = {
    Model.P1_METER: "p1dongle",
    Model.ENERGY_SOCKET: "energysocket",
    Model.WATER_METER: "watermeter",
    Model.DISPLAY: "display",
    Model.ENERGY_METER_1_PHASE: "energymeter",
    Model.ENERGY_METER_3_PHASE: "energymeter",
    Model.ENERGY_METER_EASTRON_SDM230: "energymeter",
    Model.ENERGY_METER_EASTRON_SDM630: "energymeter",
    Model.BATTERY: "battery",
}

MODEL_TO_NAME = {
    Model.P1_METER: "Wi-Fi P1 Meter",
    Model.ENERGY_SOCKET: "Wi-Fi Energy Socket",
    Model.WATER_METER: "Wi-Fi Watermeter",
    Model.DISPLAY: "Energy Display",
    Model.ENERGY_METER_1_PHASE: "Wi-Fi kWh Meter 1-phase",
    Model.ENERGY_METER_3_PHASE: "Wi-Fi kWh Meter 3-phase",
    Model.ENERGY_METER_EASTRON_SDM230: "Wi-Fi kWh Meter 1-phase",
    Model.ENERGY_METER_EASTRON_SDM630: "Wi-Fi kWh Meter 3-phase",
    Model.BATTERY: "Plug-In Battery",
}
