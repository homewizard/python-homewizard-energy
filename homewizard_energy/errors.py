"""python-homewizard-energy errors."""


class HomeWizardEnergyException(Exception):
    """Base error for python-homewizard-energy."""


class RequestError(HomeWizardEnergyException):
    """Unable to fulfill request.

    Raised when host or API cannot be reached.
    """


class WebSocketDisconnectedError(RequestError):
    """WebSocket connection could not be established, or was lost.

    This error is temporary: connecting again may succeed.
    """

    def __init__(self, message: str, close_code: int | None = None) -> None:
        """Create the error.

        Args:
            message: Description of the error.
            close_code: Code that the device gave for closing the connection,
                None when the connection ended in another way.
        """
        super().__init__(message)
        self.close_code = close_code


class InvalidUserNameError(HomeWizardEnergyException):
    """Invalid username.

    Raised when username is not valid, too short or too long.
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
