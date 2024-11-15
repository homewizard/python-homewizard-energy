"""Brand specific information for HomeWizard Energy."""

from __future__ import annotations

from dataclasses import dataclass


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
}


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
