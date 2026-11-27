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

# Models that are supported via the v2 API by this version of the library.
# Keep in sync with https://api-documentation.homewizard.com/docs/introduction#devices
# Devices of other models may enable the v2 API (e.g. with beta firmware), but are
# not reported as v2 capable by `has_v2_api` until they are added here.
SUPPORTED_V2_MODELS = frozenset(
    {
        Model.P1_METER,
        Model.ENERGY_SOCKET,
        Model.ENERGY_METER_1_PHASE,
        Model.ENERGY_METER_3_PHASE,
        Model.ENERGY_METER_EASTRON_SDM230,
        Model.ENERGY_METER_EASTRON_SDM630,
        Model.BATTERY,
    }
)

# Models that have a WebSocket in the v2 API.
# Keep in sync with https://api-documentation.homewizard.com/docs/v2/websocket
# Other models may get a WebSocket with newer firmware, but the library does not
# connect to it until they are added here.
SUPPORTED_WEBSOCKET_MODELS = frozenset(
    {
        Model.P1_METER,
        Model.ENERGY_METER_1_PHASE,
        Model.ENERGY_METER_3_PHASE,
        Model.ENERGY_METER_EASTRON_SDM230,
        Model.ENERGY_METER_EASTRON_SDM630,
        Model.BATTERY,
    }
)

MODEL_TO_NAME = {
    Model.P1_METER: "P1 Meter",
    Model.ENERGY_SOCKET: "Energy Socket",
    Model.WATER_METER: "Watermeter",
    Model.DISPLAY: "Energy Display",
    Model.ENERGY_METER_1_PHASE: "kWh Meter 1-phase",
    Model.ENERGY_METER_3_PHASE: "kWh Meter 3-phase",
    Model.ENERGY_METER_EASTRON_SDM230: "kWh Meter 1-phase",
    Model.ENERGY_METER_EASTRON_SDM630: "kWh Meter 3-phase",
    Model.BATTERY: "Plug-In Battery",
}
