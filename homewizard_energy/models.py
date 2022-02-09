"""Models for HomeWizard Energy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Device:
    """Represent Device config."""

    product_name: str | None
    product_type: str | None
    serial: str | None
    api_version: str | None
    firmware_version: str | None

    @staticmethod
    def from_dict(data: dict[str, str]) -> Device:
        """Return Device object from API response.

        Args:
            data: The data from the HomeWizard Energy `api` API.

        Returns:
            A Device object.
        """
        return Device(
            product_name=data.get("product_name"),
            product_type=data.get("product_type"),
            serial=data.get("serial"),
            api_version=data.get("api_version"),
            firmware_version=data.get("firmware_version"),
        )


@dataclass
class Data:
    """Represent Device config."""

    smr_version: int | None
    meter_model: str | None

    wifi_ssid: str | None
    wifi_strength: int | None

    total_power_import_t1_kwh: float | None
    total_power_import_t2_kwh: float | None
    total_power_export_t1_kwh: float | None
    total_power_export_t2_kwh: float | None

    active_power_w: float | None
    active_power_l1_w: float | None
    active_power_l2_w: float | None
    active_power_l3_w: float | None

    total_gas_m3: float | None
    gas_timestamp: float | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Data:
        """Return State object from API response.

        Args:
            data: The data from the HomeWizard Energy `api/v1/data` API.

        Returns:
            A State object.
        """

        def convert_gas_timestamp(timestamp: str | None) -> datetime | None:
            """Convert SRM gas-timestamp to datetime object.

            Args:
                timestamp: Timestamp string, formatted as yymmddhhmmss

            Returns:
                A datetime object.
            """
            if timestamp is None:
                return None

            return datetime.strptime(str(timestamp), "%y%m%d%H%M%S")

        return Data(
            smr_version=data.get("smr_version"),
            meter_model=data.get("meter_model"),
            wifi_ssid=data.get("wifi_ssid"),
            wifi_strength=data.get("wifi_strength"),
            total_power_import_t1_kwh=data.get("total_power_import_t1_kwh"),
            total_power_import_t2_kwh=data.get("total_power_import_t2_kwh"),
            total_power_export_t1_kwh=data.get("total_power_export_t1_kwh"),
            total_power_export_t2_kwh=data.get("total_power_export_t2_kwh"),
            active_power_w=data.get("active_power_w"),
            active_power_l1_w=data.get("active_power_l1_w"),
            active_power_l2_w=data.get("active_power_l2_w"),
            active_power_l3_w=data.get("active_power_l3_w"),
            total_gas_m3=data.get("total_gas_m3"),
            gas_timestamp=convert_gas_timestamp(data.get("gas_timestamp")),
        )


@dataclass
class State:
    """Represent current state."""

    power_on: bool | None
    switch_lock: bool | None
    brightness: int | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> dict:
        """Return State object from API response.

        Args:
            data: The data from the HomeWizard Energy `api/v1/state` API.

        Returns:
            A State object.
        """
        return State(
            power_on=data.get("power_on"),
            switch_lock=data.get("switch_lock"),
            brightness=data.get("brightness"),
        )
