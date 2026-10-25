class AuthValidationError(Exception):
    """Raised for invalid registration input (bad email, weak password, ...)."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class AuthConflictError(Exception):
    """Raised when an account already exists for the normalized email."""

    pass


class AuthUnauthorizedError(Exception):
    """Raised for any authentication failure. The exception message is for
    server-side logs only — the API always returns a fixed generic message
    regardless of the specific cause, to prevent account enumeration."""

    pass


class AuthForbiddenError(Exception):
    """Raised when an authenticated user lacks sufficient role permissions (403)."""

    pass
