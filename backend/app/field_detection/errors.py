class FieldDetectionError(Exception):
    """Base exception class for all field-detection-related errors."""

    pass


class FieldDetectionValidationError(FieldDetectionError):
    """Raised for a business-rule field-detection failure that maps to HTTP 422.

    Covers: field_detection_not_required, ocr_required, ocr_not_complete,
    supported_template_detected, field_detection_failed,
    field_detection_invalid_result.
    """

    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class FieldDetectionNotFoundError(FieldDetectionError):
    """Raised when no field-detection result exists yet for a document, or a
    referenced detected field does not exist."""

    pass


class FieldDetectionAlreadyProcessingError(FieldDetectionError):
    """Raised when a detection request is made while a prior request for the
    same document is still processing."""

    pass


class FieldDetectionProviderUnavailableError(FieldDetectionError):
    """Raised when the configured detection provider cannot be invoked."""

    pass


class FieldDetectionConfigurationError(FieldDetectionError):
    """Raised when the configured provider name is unknown or misconfigured."""

    pass
