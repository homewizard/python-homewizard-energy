"""Feature resolver for HomeWizard Energy."""

from __future__ import annotations

import re

from awesomeversion import AwesomeVersion


class Features:
    """Parse device type and version to know what features are supported."""

    version: AwesomeVersion
    device_type: str

    def __init__(self, device_type: str, version: str):
        """Create a Feature object based on input.

        Args:
            device_type: Device type eg. "HWE-P1"
            version: Firmware version eg. 1.23
        """

        # Strip any addition data from version (eg. 1.23-beta-1 -> 1.23)
        self.version = AwesomeVersion(re.findall(r"[0-9]+\.[0-9]+", version)[0])
        self.device_type = device_type.upper()

    @property
    def has_state(self) -> bool:
        """Return if device supports `state` API."""
        if self.device_type == "HWE-SKT":
            return True
        return False