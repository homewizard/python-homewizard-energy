"""Common models for HomeWizard Energy API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from mashumaro.config import BaseConfig
from mashumaro.exceptions import MissingField
from mashumaro.mixins.orjson import DataClassORJSONMixin


class BaseModel(DataClassORJSONMixin):
    """Base model for all HomeWizard models."""

    # pylint: disable-next=too-few-public-methods
    class Config(BaseConfig):
        """Mashumaro configuration."""

        serialize_by_alias = True
        omit_none = True


MODELS = {
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


def get_verification_hostname(model: str, serial_number: str) -> str:
    """Helper method to convert device model and serial to identifier

    The identifier is used to verify the device in the HomeWizard Energy API via HTTPS.
    """

    if model not in MODELS:
        raise ValueError(f"Unsupported model: {model}")

    return f"appliance/{MODELS[model]}/{serial_number}"


@dataclass(kw_only=True)
class Device(BaseModel):
    """Represent Device config."""

    product: Product | None = None
    id: str | None = None

    product_name: str = field()
    product_type: str = field()
    serial: str = field()
    api_version: str = field()
    firmware_version: str = field()

    @classmethod
    def __post_deserialize__(cls, obj: Device) -> Device:
        """Post deserialize hook for Device object."""
        _ = cls  # Unused

        obj.product = Product.from_type(obj.product_type)
        obj.id = get_verification_hostname(obj.product_type, obj.serial)
        return obj


@dataclass(kw_only=True)
class Measurement(BaseModel):
    """Represent Measurement."""

    # Deprecated, use 'System'
    wifi_ssid: str | None = field(
        default=None,
    )
    wifi_strength: int | None = field(
        default=None,
    )

    # Generic
    energy_import_kwh: float | None = field(
        default=None,
    )
    energy_import_t1_kwh: float | None = field(
        default=None,
    )
    energy_import_t2_kwh: float | None = field(
        default=None,
    )
    energy_import_t3_kwh: float | None = field(
        default=None,
    )
    energy_import_t4_kwh: float | None = field(
        default=None,
    )
    energy_export_kwh: float | None = field(
        default=None,
    )
    energy_export_t1_kwh: float | None = field(
        default=None,
    )
    energy_export_t2_kwh: float | None = field(
        default=None,
    )
    energy_export_t3_kwh: float | None = field(
        default=None,
    )
    energy_export_t4_kwh: float | None = field(
        default=None,
    )

    power_w: float | None = field(
        default=None,
    )
    power_l1_w: float | None = field(
        default=None,
    )
    power_l2_w: float | None = field(
        default=None,
    )
    power_l3_w: float | None = field(
        default=None,
    )

    voltage_v: float | None = field(
        default=None,
    )
    voltage_l1_v: float | None = field(
        default=None,
    )
    voltage_l2_v: float | None = field(
        default=None,
    )
    voltage_l3_v: float | None = field(
        default=None,
    )

    current_a: float | None = field(
        default=None,
    )
    current_l1_a: float | None = field(
        default=None,
    )
    current_l2_a: float | None = field(
        default=None,
    )
    current_l3_a: float | None = field(
        default=None,
    )

    apparent_power_va: float | None = field(
        default=None,
    )
    apparent_power_l1_va: float | None = field(
        default=None,
    )
    apparent_power_l2_va: float | None = field(
        default=None,
    )
    apparent_power_l3_va: float | None = field(
        default=None,
    )

    reactive_power_var: float | None = field(
        default=None,
    )
    reactive_power_l1_var: float | None = field(
        default=None,
    )
    reactive_power_l2_var: float | None = field(
        default=None,
    )
    reactive_power_l3_var: float | None = field(
        default=None,
    )

    power_factor: float | None = field(
        default=None,
    )
    power_factor_l1: float | None = field(
        default=None,
    )
    power_factor_l2: float | None = field(
        default=None,
    )
    power_factor_l3: float | None = field(
        default=None,
    )

    frequency_hz: float | None = field(
        default=None,
    )

    # P1 Meter specific
    timestamp: datetime | None = field(
        default=None,
        metadata={"deserialize": lambda x: Measurement.to_datetime(x)},
    )
    protocol_version: int | None = field(
        default=None,
    )
    meter_model: str | None = field(
        default=None,
    )
    unique_id: str | None = field(
        default=None,
        metadata={"deserialize": lambda x: Measurement.hex_to_readable(x)},
    )

    tariff: int | None = field(
        default=None,
    )

    voltage_sag_l1_count: int | None = field(
        default=None,
    )
    voltage_sag_l2_count: int | None = field(
        default=None,
    )
    voltage_sag_l3_count: int | None = field(
        default=None,
    )

    voltage_swell_l1_count: int | None = field(
        default=None,
    )
    voltage_swell_l2_count: int | None = field(
        default=None,
    )
    voltage_swell_l3_count: int | None = field(
        default=None,
    )

    any_power_fail_count: int | None = field(
        default=None,
    )
    long_power_fail_count: int | None = field(
        default=None,
    )

    average_power_15m_w: float | None = field(
        default=None,
    )
    monthly_power_peak_w: float | None = field(
        default=None,
    )
    monthly_power_peak_timestamp: datetime | None = field(
        default=None,
        metadata={"deserialize": lambda x: Measurement.to_datetime(x)},
    )

    external_devices: dict[str, ExternalDevice] | None = field(
        default=None,
        metadata={
            "alias": "external",
            "deserialize": lambda list: Measurement.array_to_external_device_list(list),
        },
    )

    # Watermeter Specific
    active_liter_lpm: float | None = field(
        default=None,
    )
    total_liter_m3: float | None = field(
        default=None,
    )

    # Battery Specific
    cycles: int | None = field(
        default=None,
    )
    state_of_charge_pct: float | None = field(
        default=None,
    )

    @staticmethod
    def array_to_external_device_list(devices: list[dict]) -> dict[str, ExternalDevice]:
        """Convert external device dict to list of ExternalDevice objects."""
        rv: dict[str, ExternalDevice] = {}

        for item in devices:
            try:
                device = ExternalDevice.from_dict(item)
            except MissingField as e:
                print(f"Error converting external device: {e}")
                continue
            rv[f"{device.type}_{device.unique_id}"] = device

        return rv

    @staticmethod
    def to_datetime(timestamp: str | int | None) -> datetime | None:
        """Convert DSRM gas-timestamp to datetime object.

        Args:
            timestamp: Timestamp string, formatted as YYMMDDHHMMSS or YYYY-MM-DDTHH:MM:SS

        Returns:
            A datetime object.
        """

        if timestamp is None:
            return None

        if isinstance(timestamp, int):
            # V1 API uses int for timestamp
            return datetime.strptime(str(timestamp), "%y%m%d%H%M%S")

        return datetime.fromisoformat(timestamp)

    @staticmethod
    def hex_to_readable(value: str | None) -> str | None:
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

    @classmethod
    # pylint: disable=too-many-statements
    def __pre_deserialize__(cls, d: dict[Any, Any]) -> dict[Any, Any]:
        _ = cls  # Unused

        if "wifi_ssid" not in d:
            # This is a v2 API response, no need to remap
            return d

        d["protocol_version"] = d.get("smr_version")
        d["meter_model"] = d.get("meter_model")
        d["unique_id"] = d.get("unique_meter_id")
        d["tariff"] = d.get("active_tariff")
        d["energy_import_kwh"] = d.get("total_power_import_kwh")
        d["energy_import_t1_kwh"] = d.get("total_power_import_t1_kwh")
        d["energy_import_t2_kwh"] = d.get("total_power_import_t2_kwh")
        d["energy_import_t3_kwh"] = d.get("total_power_import_t3_kwh")
        d["energy_import_t4_kwh"] = d.get("total_power_import_t4_kwh")
        d["energy_export_kwh"] = d.get("total_power_export_kwh")
        d["energy_export_t1_kwh"] = d.get("total_power_export_t1_kwh")
        d["energy_export_t2_kwh"] = d.get("total_power_export_t2_kwh")
        d["energy_export_t3_kwh"] = d.get("total_power_export_t3_kwh")
        d["energy_export_t4_kwh"] = d.get("total_power_export_t4_kwh")
        d["power_w"] = d.get("active_power_w")
        d["power_l1_w"] = d.get("active_power_l1_w")
        d["power_l2_w"] = d.get("active_power_l2_w")
        d["power_l3_w"] = d.get("active_power_l3_w")
        d["voltage_v"] = d.get("active_voltage_v")
        d["voltage_l1_v"] = d.get("active_voltage_l1_v")
        d["voltage_l2_v"] = d.get("active_voltage_l2_v")
        d["voltage_l3_v"] = d.get("active_voltage_l3_v")
        d["current_a"] = d.get("active_current_a")
        d["current_l1_a"] = d.get("active_current_l1_a")
        d["current_l2_a"] = d.get("active_current_l2_a")
        d["current_l3_a"] = d.get("active_current_l3_a")
        d["apparent_power_va"] = d.get("active_apparent_power_va")
        d["apparent_power_l1_va"] = d.get("active_apparent_power_l1_va")
        d["apparent_power_l2_va"] = d.get("active_apparent_power_l2_va")
        d["apparent_power_l3_va"] = d.get("active_apparent_power_l3_va")
        d["reactive_power_var"] = d.get("active_reactive_power_var")
        d["reactive_power_l1_var"] = d.get("active_reactive_power_l1_var")
        d["reactive_power_l2_var"] = d.get("active_reactive_power_l2_var")
        d["reactive_power_l3_var"] = d.get("active_reactive_power_l3_var")
        d["power_factor"] = d.get("active_power_factor")
        d["power_factor_l1"] = d.get("active_power_factor_l1")
        d["power_factor_l2"] = d.get("active_power_factor_l2")
        d["power_factor_l3"] = d.get("active_power_factor_l3")
        d["frequency_hz"] = d.get("active_frequency_hz")
        d["voltage_sag_l1_count"] = d.get("voltage_sag_l1_count")
        d["voltage_sag_l2_count"] = d.get("voltage_sag_l2_count")
        d["voltage_sag_l3_count"] = d.get("voltage_sag_l3_count")
        d["voltage_swell_l1_count"] = d.get("voltage_swell_l1_count")
        d["voltage_swell_l2_count"] = d.get("voltage_swell_l2_count")
        d["voltage_swell_l3_count"] = d.get("voltage_swell_l3_count")
        d["any_power_fail_count"] = d.get("any_power_fail_count")
        d["long_power_fail_count"] = d.get("long_power_fail_count")
        d["average_power_15m_w"] = d.get("active_power_average_w")
        d["monthly_power_peak_w"] = d.get("montly_power_peak_w")
        d["monthly_power_peak_timestamp"] = d.get("montly_power_peak_timestamp")
        d["active_liter_lpm"] = d.get("active_liter_lpm")
        d["total_liter_m3"] = d.get("total_liter_m3")
        d["external_devices"] = d.get("external_devices")

        return d


@dataclass
class ExternalDevice(BaseModel):
    """Represents externally connected device."""

    class DeviceType(Enum):
        """Device type allocations."""

        GAS_METER = "gas_meter"
        HEAT_METER = "heat_meter"
        WARM_WATER_METER = "warm_water_meter"
        WATER_METER = "water_meter"
        INLET_HEAT_METER = "inlet_heat_meter"

    unique_id: datetime = field(
        default=None, metadata={"deserialize": lambda x: Measurement.hex_to_readable(x)}
    )

    type: DeviceType | None = field(
        default=None,
        metadata={
            "deserialize": lambda x: ExternalDevice.DeviceType(x)
            if x in ExternalDevice.DeviceType.__members__.values()
            else None
        },
    )
    value: float = field(default=0.0)
    unit: str = field(default="")
    timestamp: datetime = field(
        default=None, metadata={"deserialize": lambda x: Measurement.to_datetime(x)}
    )


@dataclass(frozen=True)
class Product:
    """Represent a product."""

    model: str
    name: str | None
    url: str | None
    description: str | None

    def __str__(self):
        """Return a string representation of the product."""
        return f"HomeWizard {self.name} - {self.model}"

    def __hash__(self):
        """Hash a product for unit-test snapshots."""
        return hash((self.model, self.name, self.url, self.description))

    def __eq__(self, other):
        """Compare two products."""
        if isinstance(other, Product):
            return (
                self.model == other.model
                and self.name == other.name
                and self.url == other.url
                and self.description == other.description
            )
        return False

    @staticmethod
    def from_type(product_type: str, _: str | None = None) -> Product | None:
        """Return a Product object from a type.

        :param type: The type of the product.
        :param locale: The locale to use for the description. Currently ignored. Should be an ISO 639-1 language code.
        """

        # pylint: disable=unused-argument

        for product in PRODUCTS:
            if product.model == product_type:
                return product
        return None


PRODUCTS = {
    Product(
        "HWE-P1",
        "Wi-Fi P1 Meter",
        "https://www.homewizard.com/p1-meter/",
        "The HomeWizard P1 Meter gives you detailed insight in your electricity-, gas consumption and solar surplus.",
    ),
    Product(
        "HWE-SKT",
        "Wi-Fi Energy Socket",
        "https://www.homewizard.com/energy-socket/",
        "Measure and switch every device.",
    ),
    Product(
        "HWE-WTR",
        "Wi-Fi Watermeter",
        "https://www.homewizard.com/watermeter/",
        "Real-time water consumption insights",
    ),
    Product(
        "HWE-KWH1",
        "Wi-Fi kWh Meter 1-phase",
        "https://www.homewizard.com/kwh-meter/",
        "Measure solar panels, car chargers and more.",
    ),
    Product(
        "HWE-KWH3",
        "Wi-Fi kWh Meter 3-phase",
        "https://www.homewizard.com/kwh-meter/",
        "Measure solar panels, car chargers and more.",
    ),
    Product(
        "SDM230-wifi",
        "Wi-Fi kWh Meter 1-phase",
        "https://www.homewizard.com/kwh-meter/",
        "Measure solar panels, car chargers and more.",
    ),
    Product(
        "SDM630-wifi",
        "Wi-Fi kWh Meter 3-phase",
        "https://www.homewizard.com/kwh-meter/",
        "Measure solar panels, car chargers and more.",
    ),
    Product(
        "HWE-BAT",
        "Plug-In Battery",
        "https://www.homewizard.com/plug-in-battery/",
        "Solar energy, day and night.",
    ),
}


@dataclass(kw_only=True)
class State(BaseModel):
    """Represent current state."""

    power_on: bool | None = field(
        default=None,
    )
    switch_lock: bool | None = field(
        default=None,
    )
    brightness: int | None = field(
        default=None,
    )


@dataclass
class SystemUpdate(BaseModel):
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


@dataclass(kw_only=True)
class System(BaseModel):
    """Represent System config."""

    wifi_ssid: str | None = field(default=None)
    wifi_rssi_db: int | None = field(default=None)
    cloud_enabled: bool | None = field(default=None)
    uptime_s: int | None = field(default=None)
    status_led_brightness_pct: int | None = field(default=None)
    api_v1_enabled: bool | None = field(default=None)


@dataclass(kw_only=True)
class Token(BaseModel):
    """Represent Token."""

    token: str = field()
