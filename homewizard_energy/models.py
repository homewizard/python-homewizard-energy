"""Common models for HomeWizard Energy API."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class Device:
    """Represent Device config."""

    product: Product | None
    product_name: str | None
    product_type: str | None
    serial: str | None
    api_version: str | None
    firmware_version: str | None
    id: str | None

    @staticmethod
    def from_dict(data: dict[str, str]) -> Device:
        """Return Device object from API response.

        This model is common for both v1 and v2 API.

        Args:
            data: The data from the HomeWizard Energy `api` API.

        Returns:
            A Device object.
        """

        try:
            _id = get_verification_hostname(
                data.get("product_type"), data.get("serial")
            )
        except ValueError:
            _id = None

        return Device(
            product=Product.from_type(data.get("product_type")),
            product_name=data.get("product_name"),
            product_type=data.get("product_type"),
            serial=data.get("serial"),
            api_version=data.get("api_version"),
            firmware_version=data.get("firmware_version"),
            id=_id,
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
