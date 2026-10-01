class AppError(Exception):
    """Base of the app's own errors; the message is shown to the user as is."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """An object the request refers to doesn't exist."""

    status_code = 404


class UnauthorizedError(AppError):
    """The request needs a signed-in user, or the credentials are wrong."""

    status_code = 401


class ConflictError(AppError):
    """The request contradicts the current state of the data."""

    status_code = 409


class ConfigError(RuntimeError):
    """The service is misconfigured (missing or wrong settings)."""
