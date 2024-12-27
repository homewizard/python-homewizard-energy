"""Models for HomeWizard Energy v1."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class Data:
    """Represent Device config."""

    wifi_ssid: str | None
    wifi_strength: int | None

    smr_version: int | None
    meter_model: str | None
    unique_meter_id: str | None

    active_tariff: int | None

    total_energy_import_kwh: float | None
    total_energy_import_t1_kwh: float | None
    total_energy_import_t2_kwh: float | None
    total_energy_import_t3_kwh: float | None
    total_energy_import_t4_kwh: float | None
    total_energy_export_kwh: float | None
    total_energy_export_t1_kwh: float | None
    total_energy_export_t2_kwh: float | None
    total_energy_export_t3_kwh: float | None
    total_energy_export_t4_kwh: float | None

    active_power_w: float | None
    active_power_l1_w: float | None
    active_power_l2_w: float | None
    active_power_l3_w: float | None

    active_voltage_v: float | None
    active_voltage_l1_v: float | None
    active_voltage_l2_v: float | None
    active_voltage_l3_v: float | None

    active_current_a: float | None
    active_current_l1_a: float | None
    active_current_l2_a: float | None
    active_current_l3_a: float | None

    active_apparent_power_va: float | None
    active_apparent_power_l1_va: float | None
    active_apparent_power_l2_va: float | None
    active_apparent_power_l3_va: float | None

    active_reactive_power_var: float | None
    active_reactive_power_l1_var: float | None
    active_reactive_power_l2_var: float | None
    active_reactive_power_l3_var: float | None

    active_power_factor: float | None
    active_power_factor_l1: float | None
    active_power_factor_l2: float | None
    active_power_factor_l3: float | None

    active_frequency_hz: float | None

    voltage_sag_l1_count: int | None
    voltage_sag_l2_count: int | None
    voltage_sag_l3_count: int | None

    voltage_swell_l1_count: int | None
    voltage_swell_l2_count: int | None
    voltage_swell_l3_count: int | None

    any_power_fail_count: int | None
    long_power_fail_count: int | None

    active_power_average_w: float | None
    monthly_power_peak_w: float | None
    monthly_power_peak_timestamp: datetime | None

    total_gas_m3: float | None
    gas_timestamp: datetime | None
    gas_unique_id: str | None

    active_liter_lpm: float | None
    total_liter_m3: float | None

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

        return datetime.strptime(str(timestamp), "%y%m%d%H%M%S")

    @staticmethod
    def convert_hex_string_to_readable(value: str | None) -> str | None:
        """Convert hex 'SMS' string to readable string, if possible.

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
            with suppress(ValueError, KeyError):
                device = ExternalDevice.from_dict(external)
                type_unique_id = f"{external.get('type')}_{device.unique_id}"

            devices[type_unique_id] = device

        return devices

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Data:
        """Return State object from API response.

        Args:
            data: The data from the HomeWizard Energy `api/v1/data` API.

        Returns:
            A State object.
        """

        return Data(
            wifi_ssid=data.get("wifi_ssid"),
            wifi_strength=data.get("wifi_strength"),
            smr_version=data.get("smr_version"),
            meter_model=data.get("meter_model"),
            unique_meter_id=Data.convert_hex_string_to_readable(data.get("unique_id")),
            active_tariff=data.get("active_tariff"),
            total_energy_import_kwh=data.get(
                "total_power_import_kwh", data.get("total_power_import_t1_kwh")
            ),
            total_energy_import_t1_kwh=data.get("total_power_import_t1_kwh"),
            total_energy_import_t2_kwh=data.get("total_power_import_t2_kwh"),
            total_energy_import_t3_kwh=data.get("total_power_import_t3_kwh"),
            total_energy_import_t4_kwh=data.get("total_power_import_t4_kwh"),
            total_energy_export_kwh=data.get(
                "total_power_export_kwh", data.get("total_power_export_t1_kwh")
            ),
            total_energy_export_t1_kwh=data.get("total_power_export_t1_kwh"),
            total_energy_export_t2_kwh=data.get("total_power_export_t2_kwh"),
            total_energy_export_t3_kwh=data.get("total_power_export_t3_kwh"),
            total_energy_export_t4_kwh=data.get("total_power_export_t4_kwh"),
            active_power_w=data.get("active_power_w"),
            active_power_l1_w=data.get("active_power_l1_w"),
            active_power_l2_w=data.get("active_power_l2_w"),
            active_power_l3_w=data.get("active_power_l3_w"),
            active_voltage_v=data.get("active_voltage_v"),
            active_voltage_l1_v=data.get("active_voltage_l1_v"),
            active_voltage_l2_v=data.get("active_voltage_l2_v"),
            active_voltage_l3_v=data.get("active_voltage_l3_v"),
            active_current_a=data.get("active_current_a"),
            active_current_l1_a=data.get("active_current_l1_a"),
            active_current_l2_a=data.get("active_current_l2_a"),
            active_current_l3_a=data.get("active_current_l3_a"),
            active_apparent_power_va=data.get("active_apparent_power_va"),
            active_apparent_power_l1_va=data.get("active_apparent_power_l1_va"),
            active_apparent_power_l2_va=data.get("active_apparent_power_l2_va"),
            active_apparent_power_l3_va=data.get("active_apparent_power_l3_va"),
            active_reactive_power_var=data.get("active_reactive_power_var"),
            active_reactive_power_l1_var=data.get("active_reactive_power_l1_var"),
            active_reactive_power_l2_var=data.get("active_reactive_power_l2_var"),
            active_reactive_power_l3_var=data.get("active_reactive_power_l3_var"),
            active_power_factor=data.get("active_power_factor"),
            active_power_factor_l1=data.get("active_power_factor_l1"),
            active_power_factor_l2=data.get("active_power_factor_l2"),
            active_power_factor_l3=data.get("active_power_factor_l3"),
            active_frequency_hz=data.get("active_frequency_hz"),
            voltage_sag_l1_count=data.get("voltage_sag_l1_count"),
            voltage_sag_l2_count=data.get("voltage_sag_l2_count"),
            voltage_sag_l3_count=data.get("voltage_sag_l3_count"),
            voltage_swell_l1_count=data.get("voltage_swell_l1_count"),
            voltage_swell_l2_count=data.get("voltage_swell_l2_count"),
            voltage_swell_l3_count=data.get("voltage_swell_l3_count"),
            any_power_fail_count=data.get("any_power_fail_count"),
            long_power_fail_count=data.get("long_power_fail_count"),
            active_power_average_w=data.get("active_power_average_w"),
            monthly_power_peak_w=data.get("montly_power_peak_w"),
            monthly_power_peak_timestamp=Data.convert_timestamp_to_datetime(
                data.get("montly_power_peak_timestamp")
            ),
            total_gas_m3=data.get("total_gas_m3"),
            gas_timestamp=Data.convert_timestamp_to_datetime(data.get("gas_timestamp")),
            gas_unique_id=Data.convert_hex_string_to_readable(
                data.get("gas_unique_id")
            ),
            active_liter_lpm=data.get("active_liter_lpm"),
            total_liter_m3=data.get("total_liter_m3"),
            external_devices=Data.get_external_devices(data.get("external")),
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
            unique_id=Data.convert_hex_string_to_readable(data.get("unique_id")),
            meter_type=ExternalDevice.DeviceType.from_string(data.get("type", "")),
            value=data.get("value", 0),
            unit=data.get("unit", ""),
            timestamp=datetime.strptime(str(data.get("timestamp")), "%y%m%d%H%M%S"),
        )


@dataclass
class State:
    """Represent current state."""

    power_on: bool | None
    switch_lock: bool | None
    brightness: int | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> State:
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


@dataclass
class System:
    """Represent current state."""

    cloud_enabled: bool | None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> System:
        """Return System object from API response.

        Args:
            data: The data from the HomeWizard Energy `api/v1/system` API.

        Returns:
            A System object.
        """
        return System(
            cloud_enabled=data.get("cloud_enabled"),
        )
