"""python-homewizard-energy errors."""


class HomeWizardEnergyException(Exception):
    """Base error for python-homewizard-energy."""


class RequestError(HomeWizardEnergyException):
    """Unable to fulfill request.

    Raised when host or API cannot be reached.
    """


class InvalidStateError(HomeWizardEnergyException):
    """Raised when the device is not in the correct state."""


class UnsupportedError(HomeWizardEnergyException):
    """Raised when the device is not supported from this library."""


class DisabledError(HomeWizardEnergyException):
    """Raised when device API is disabled. User has to enable API in app."""
