class DocumentError(Exception):
    """Base exception class for all document-related errors."""
    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a source document is not found."""
    pass


class DocumentValidationError(DocumentError):
    """Raised when document validations fail (file size, extension, checksum, encrypted, etc.)."""
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class DocumentUnauthorizedError(DocumentError):
    """Raised when ownership token verification fails."""
    pass


class DocumentStateConflictError(DocumentError):
    """Raised when document states (e.g. status) are in conflict with the requested operation."""
    pass
