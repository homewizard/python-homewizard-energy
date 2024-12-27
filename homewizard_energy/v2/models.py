"""Models for HomeWizard Energy v2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class Measurement:
    """Represent Measurement."""

    protocol_version: int | None
    meter_model: str | None
    unique_id: str | None

    tariff: int | None

    energy_import_kwh: float | None
    energy_import_t1_kwh: float | None
    energy_import_t2_kwh: float | None
    energy_import_t3_kwh: float | None
    energy_import_t4_kwh: float | None
    energy_export_kwh: float | None
    energy_export_t1_kwh: float | None
    energy_export_t2_kwh: float | None
    energy_export_t3_kwh: float | None
    energy_export_t4_kwh: float | None

    power_w: float | None
    power_l1_w: float | None
    power_l2_w: float | None
    power_l3_w: float | None

    voltage_l1_v: float | None
    voltage_l2_v: float | None
    voltage_l3_v: float | None

    current_a: float | None
    current_l1_a: float | None
    current_l2_a: float | None
    current_l3_a: float | None

    frequency_hz: float | None

    cycles: int | None
    state_of_charge_pct: float | None

    voltage_sag_l1_count: int | None
    voltage_sag_l2_count: int | None
    voltage_sag_l3_count: int | None

    voltage_swell_l1_count: int | None
    voltage_swell_l2_count: int | None
    voltage_swell_l3_count: int | None

    any_power_fail_count: int | None
    long_power_fail_count: int | None

    average_power_15m_w: float | None
    monthly_power_peak_w: float | None
    monthly_power_peak_timestamp: datetime | None

    external_devices: dict[str, ExternalDevice] | None

    @staticmethod
    def convert_timestamp_to_datetime(timestamp: str | None) -> datetime | None:
        """Convert SRM gas-timestamp to datetime object.

        Args:
            timestamp: Timestamp string, formatted as yymmddhhmmss

        Returns:
            A datetime object.
        """
        if timestamp is None:
            return None

        return datetime.fromisoformat(timestamp)

    @staticmethod
    def convert_hex_string_to_readable(value: str | None) -> str | None:
        """Convert hex string to readable string, if possible.

        Args:
            value: String to convert, e.g. '4E47475955'

        Returns:
            A string formatted or original value when failed.
        """
        try:
            return bytes.fromhex(value).decode("utf-8")
        except (TypeError, ValueError):
            return value

    @staticmethod
    def get_external_devices(
        external_devices: list[dict[str, Any]] | None,
    ) -> dict[str, ExternalDevice] | None:
        """Convert external device object to ExternalDevice Object List."""
        devices: dict[str, ExternalDevice] = {}

        if external_devices is None:
            return None

        for external in external_devices:
            try:
                device = ExternalDevice.from_dict(external)
            except KeyError:
                continue

            type_unique_id = f"{external.get('type')}_{device.unique_id}"
            devices[type_unique_id] = device

        return devices

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Measurement:
        """Return Measurement object from API response.

        Args:
            data: The data from the HomeWizard Energy `api/v1/measurement` API.

        Returns:
            A Measurement object.
        """
        return Measurement(
            protocol_version=data.get("smr_version"),
            meter_model=data.get("meter_model"),
            unique_id=Measurement.convert_hex_string_to_readable(data.get("unique_id")),
            tariff=data.get("active_tariff"),
            energy_import_kwh=data.get("energy_import_kwh"),
            energy_import_t1_kwh=data.get("energy_import_t1_kwh"),
            energy_import_t2_kwh=data.get("energy_import_t2_kwh"),
            energy_import_t3_kwh=data.get("energy_import_t3_kwh"),
            energy_import_t4_kwh=data.get("energy_import_t4_kwh"),
            energy_export_kwh=data.get("energy_export_kwh"),
            energy_export_t1_kwh=data.get("energy_export_t1_kwh"),
            energy_export_t2_kwh=data.get("energy_export_t2_kwh"),
            energy_export_t3_kwh=data.get("energy_export_t3_kwh"),
            energy_export_t4_kwh=data.get("energy_export_t4_kwh"),
            power_w=data.get("power_w"),
            power_l1_w=data.get("power_l1_w"),
            power_l2_w=data.get("power_l2_w"),
            power_l3_w=data.get("power_l3_w"),
            voltage_l1_v=data.get("voltage_l1_v"),
            voltage_l2_v=data.get("voltage_l2_v"),
            voltage_l3_v=data.get("voltage_l3_v"),
            current_a=data.get("current_a"),
            current_l1_a=data.get("current_l1_a"),
            current_l2_a=data.get("current_l2_a"),
            current_l3_a=data.get("current_l3_a"),
            frequency_hz=data.get("frequency_hz"),
            cycles=data.get("cycles"),
            state_of_charge_pct=data.get("state_of_charge_pct"),
            voltage_sag_l1_count=data.get("voltage_sag_l1_count"),
            voltage_sag_l2_count=data.get("voltage_sag_l2_count"),
            voltage_sag_l3_count=data.get("voltage_sag_l3_count"),
            voltage_swell_l1_count=data.get("voltage_swell_l1_count"),
            voltage_swell_l2_count=data.get("voltage_swell_l2_count"),
            voltage_swell_l3_count=data.get("voltage_swell_l3_count"),
            any_power_fail_count=data.get("any_power_fail_count"),
            long_power_fail_count=data.get("long_power_fail_count"),
            average_power_15m_w=data.get("average_power_15m_w"),
            monthly_power_peak_w=data.get("monthly_power_peak_w"),
            monthly_power_peak_timestamp=Measurement.convert_timestamp_to_datetime(
                data.get("monthly_power_peak_timestamp")
            ),
            external_devices=Measurement.get_external_devices(data.get("external")),
        )


@dataclass
class ExternalDevice:
    """Represents externally connected device."""

    class DeviceType(Enum):
        """Device type allocations.

        Based on:
          https://oms-group.org/fileadmin/files/download4all/omsSpezifikationen/generation4/spezifikation/vol2/OMS-Spec_Vol2_Primary_v442.pdf
          Page 18, Chapter 2.3, Table 2
        """

        UNKNOWN = -1
        GAS_METER = 3
        HEAT_METER = 4
        WARM_WATER_METER = 6
        WATER_METER = 7
        INLET_HEAT_METER = 12

        @staticmethod
        def from_string(value: str) -> ExternalDevice.DeviceType:
            """Convert string to enum."""
            try:
                return {
                    "gas_meter": ExternalDevice.DeviceType.GAS_METER,
                    "heat_meter": ExternalDevice.DeviceType.HEAT_METER,
                    "warm_water_meter": ExternalDevice.DeviceType.WARM_WATER_METER,
                    "water_meter": ExternalDevice.DeviceType.WATER_METER,
                    "inlet_heat_meter": ExternalDevice.DeviceType.INLET_HEAT_METER,
                }[value]
            except KeyError:
                return ExternalDevice.DeviceType.UNKNOWN

    unique_id: str
    meter_type: DeviceType
    value: float
    unit: str
    timestamp: datetime

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ExternalDevice:
        """Return State object from API response.

        Args:
            data: The data from a external device in the HomeWizard Energy
            `api/v1/state` API.
        Returns:
            An ExternalDevice Device object.
        """
        if data.get("unique_id") is None:
            raise KeyError("unique_id must be set")

        return ExternalDevice(
            unique_id=Measurement.convert_hex_string_to_readable(data.get("unique_id")),
            meter_type=ExternalDevice.DeviceType.from_string(data.get("type", "")),
            value=data.get("value", 0),
            unit=data.get("unit", ""),
            timestamp=Measurement.convert_timestamp_to_datetime(data.get("timestamp")),
        )


@dataclass
class SystemUpdate:
    """Represent System update config."""

    cloud_enabled: bool = field(default=None)
    status_led_brightness_pct: int = field(default=None)
    api_v1_enabled: bool | None = field(default=None)

    def as_dict(self) -> dict[str, bool | int]:
        """Return SystemUpdate object as dict.

        Only include values that are not None.
        """
        _dict = {k: v for k, v in asdict(self).items() if v is not None}

        if not _dict:
            raise ValueError("No values to update")

        return _dict


@dataclass
class System:
    """Represent System config."""

    wifi_ssid: str
    wifi_rssi_db: int
    cloud_enabled: bool
    uptime_s: str
    status_led_brightness_pct: int
    api_v1_enabled: bool | None

    @staticmethod
    def from_dict(data: dict[str, str]) -> System:
        """Return System object from API response.

        Args:
            data: The data from the HomeWizard Energy `api/v2/system` API.

        Returns:
            A System object.
        """
        return System(
            wifi_ssid=data.get("wifi_ssid"),
            wifi_rssi_db=data.get("wifi_rssi_db"),
            cloud_enabled=data.get("cloud_enabled"),
            uptime_s=data.get("uptime_s"),
            status_led_brightness_pct=data.get("status_led_brightness_pct"),
            api_v1_enabled=data.get("api_v1_enabled"),
        )
