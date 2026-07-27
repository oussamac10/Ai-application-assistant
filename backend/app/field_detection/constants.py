"""Field-detection-wide constants: field-type, status, and source vocabularies."""

FIELD_TYPES = (
    "text",
    "multiline_text",
    "date",
    "email",
    "phone",
    "address",
    "number",
    "currency",
    "checkbox",
    "radio",
    "select",
    "multiple_choice",
    "signature",
    "unknown",
)

# Confidence below this threshold is never trusted as a specific field_type;
# normalization.py downgrades such candidates to "unknown" rather than
# inventing a type from weak evidence.
LOW_CONFIDENCE_THRESHOLD = 0.4

DETECTION_STATUSES = (
    "pending",
    "processing",
    "completed",
    "failed",
    "expired",
    "deleted",
)

REVIEW_STATUSES = (
    "pending_review",
    "confirmed",
    "edited",
    "rejected",
)

# Where a candidate's evidence (text/coordinates) originated.
SOURCE_TYPES = (
    "native",
    "ocr",
    "acroform",
)
