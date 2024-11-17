"""Constants for HomeWizard Energy."""

from enum import StrEnum

SUPPORTED_API_VERSION = "2.0.0"

SUPPORTS_STATE = ["HWE-SKT"]
SUPPORTS_IDENTIFY = ["HWE-SKT", "HWE-P1", "HWE-WTR"]


class WebsocketTopic(StrEnum):
    """Websocket topics."""

    DEVICE = "device"
    MEASUREMENT = "measurement"
    SYSTEM = "system"
