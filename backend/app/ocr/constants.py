"""OCR-wide constants: supported languages and status/error code vocabularies."""

# Application language code -> Tesseract language code.
# Only these four are supported; anything else is rejected at the eligibility check.
SUPPORTED_OCR_LANGUAGES: dict[str, str] = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "ar": "ara",
}

OCR_STATUSES = (
    "pending",
    "processing",
    "completed",
    "failed",
    "expired",
    "deleted",
)
