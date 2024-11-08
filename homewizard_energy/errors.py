"""python-homewizard-energy errors."""


class HomeWizardEnergyException(Exception):
    """Base error for python-homewizard-energy."""


class RequestError(HomeWizardEnergyException):
    """Unable to fulfill request.

    Raised when host or API cannot be reached.
    """


class ResponseError(HomeWizardEnergyException):
    """API responded unexpected."""


class NotFoundError(HomeWizardEnergyException):
    """Request not found.

    Raised when API responds with '404'
    """


class InvalidStateError(HomeWizardEnergyException):
    """Raised when the device is not in the correct state."""


class UnsupportedError(HomeWizardEnergyException):
    """Raised when the device is not supported from this library."""


class DisabledError(HomeWizardEnergyException):
    """Raised when device API is disabled. User has to enable API in app."""


class UnauthorizedError(HomeWizardEnergyException):
    """Raised when request is not authorized."""
