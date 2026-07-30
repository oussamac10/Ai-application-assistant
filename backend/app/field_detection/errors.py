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


# Safe, machine-readable codes for Azure Document Intelligence failures
# (Phase 14). These are internal: the API layer maps every one of them to a
# generic "document could not be processed" message. They must never carry
# credentials, endpoint URLs, Azure stack traces, raw SDK/JSON payloads, or
# document text — only the code plus a short static description.
AZURE_ERROR_CODES = (
    "azure_not_configured",
    "azure_authentication_failed",
    "azure_rate_limited",
    "azure_timeout",
    "azure_invalid_response",
    "azure_processing_failed",
)


class AzureDocumentIntelligenceError(FieldDetectionError):
    """A failure talking to (or interpreting a response from) Azure
    Document Intelligence.

    `error_code` is one of AZURE_ERROR_CODES. `request_id` is Azure's own
    correlation id when the response carried one — kept for internal
    diagnostics/logging only, never returned to a caller.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        request_id: str | None = None,
    ):
        super().__init__(message)
        if error_code not in AZURE_ERROR_CODES:
            raise ValueError(f"Unknown Azure error code '{error_code}'.")
        self.error_code = error_code
        self.request_id = request_id
