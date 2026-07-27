class ApplicationNotFoundError(Exception):
    """Raised when an application (FormSession) does not exist, is soft
    deleted, or is not owned by the requesting user. The same message is
    used for all three cases so a caller cannot use this to distinguish
    "does not exist" from "belongs to someone else"."""

    pass


class ApplicationUnauthorizedError(Exception):
    """Raised when a claim is attempted with a missing/invalid ownership
    token, or against an application already claimed by a different
    account. Both cases return the same generic message."""

    pass


class ApplicationValidationError(Exception):
    """Raised for invalid application mutation input (e.g. an empty or
    overlong title)."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code
