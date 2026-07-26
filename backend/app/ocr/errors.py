class OCRError(Exception):
    """Base exception class for all OCR-related errors."""

    pass


class OCRValidationError(OCRError):
    """Raised for a business-rule OCR failure that maps to HTTP 422.

    Covers: ocr_not_required, ocr_failed, ocr_invalid_result, unsupported_language.
    """

    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class OCRNotFoundError(OCRError):
    """Raised when no OCR result exists yet for a document."""

    pass


class OCRAlreadyProcessingError(OCRError):
    """Raised when an OCR request is made while a prior request is still processing."""

    pass


class OCRProviderUnavailableError(OCRError):
    """Raised when the configured OCR provider cannot be reached or invoked."""

    pass


class OCRTimeoutError(OCRError):
    """Raised when OCR processing exceeds the configured timeout."""

    pass


class OCRConfigurationError(OCRError):
    """Raised when the configured OCR provider name is unknown or misconfigured."""

    pass
