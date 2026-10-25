"""OCR-wide constants: supported languages and status/error code vocabularies."""

# Application language code -> Tesseract language code.
# "auto" runs multi-script recognition independent of userLanguage so foreign
# administrative forms are never forced through the applicant's UI script.
SUPPORTED_OCR_LANGUAGES: dict[str, str] = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "ar": "ara",
    "tr": "tur",
    "uk": "ukr",
    "es": "spa",
    "auto": "deu+eng+fra+ara+tur+ukr+spa",
}

OCR_STATUSES = (
    "pending",
    "processing",
    "completed",
    "failed",
    "expired",
    "deleted",
)
