"""Opening PDFs that are encrypted but not actually locked.

Most government forms are encrypted. Not to keep anyone out — to set
*permissions*: no printing, no editing, no extraction. The PDF standard
implements that with an owner password and an **empty user password**, so any
reader opens the file without asking for anything. `32-41-1268-antrag-
aufenthaltserlaubnis.pdf` (Landeshauptstadt Stuttgart) is exactly this.

The old check was:

    if reader.is_encrypted:
        raise DocumentValidationError("PDF is encrypted or password-protected.")

`is_encrypted` answers "does this file have an encryption dictionary?", which
for these documents is yes — and says nothing about whether it can be read. So a
form that opens fine in every PDF viewer was rejected at upload, and the user
was told to supply a password that does not exist.

The right question is not "is it encrypted?" but "can we open it?", and the only
way to answer that is to try:

    reader.decrypt("")   # 0 = wrong password, 1/2 = opened

Reading the pages afterwards matters too. pypdf reports success on
`decrypt("")` and then fails on first access when the AES provider is missing,
which is a *deployment* problem, not a document one — it must not be reported to
the user as a password problem. Hence `cryptography` in requirements.txt and the
page probe below.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pypdf

from app.documents.errors import DocumentValidationError

logger = logging.getLogger(__name__)

# Error codes. Distinct on purpose: the frontend can only say something useful
# ("upload an unlocked copy") when it can tell a genuinely locked file from a
# broken one.
PDF_PASSWORD_REQUIRED = "pdf_password_required"
PDF_DECRYPTION_FAILED = "pdf_decryption_failed"
PDF_INVALID = "pdf_invalid"

# pypdf's decrypt() return values. 0 means the password was rejected; 1 and 2
# mean it was accepted as the user and owner password respectively.
_DECRYPT_FAILED = 0


def open_pdf(source: str | Path) -> pypdf.PdfReader:
    """Returns a readable `PdfReader`, decrypting with an empty password.

    Raises `DocumentValidationError` only when the file genuinely cannot be
    read. Never includes the underlying exception text: pypdf error messages
    can carry object contents, and document contents are private
    (`docs/claude/working-rules.md`).
    """
    path = Path(source)
    try:
        reader = pypdf.PdfReader(path)
    except Exception as exc:
        logger.info("PDF could not be parsed (%s)", type(exc).__name__)
        raise DocumentValidationError(
            "The file could not be read as a PDF.", PDF_INVALID
        ) from exc

    if not reader.is_encrypted:
        return reader

    try:
        opened = reader.decrypt("")
    except Exception as exc:
        # A dependency gap (no AES provider) or a malformed encryption
        # dictionary. Either way it is not the user's password.
        logger.warning(
            "PDF decryption failed with an empty password (%s)", type(exc).__name__
        )
        raise DocumentValidationError(
            "The PDF could not be decrypted.", PDF_DECRYPTION_FAILED
        ) from exc

    if opened == _DECRYPT_FAILED:
        # The one case where the user really does need to do something.
        raise DocumentValidationError(
            "This PDF requires a password.", PDF_PASSWORD_REQUIRED
        )

    # `decrypt` succeeding is not proof the content is reachable — pypdf defers
    # the actual work to first access. Probe now, so a deployment problem
    # surfaces here as a decryption failure rather than later as a mysterious
    # empty document.
    try:
        _ = len(reader.pages)
    except Exception as exc:
        logger.warning(
            "PDF decrypted but its pages are unreadable (%s)", type(exc).__name__
        )
        raise DocumentValidationError(
            "The PDF could not be decrypted.", PDF_DECRYPTION_FAILED
        ) from exc

    logger.info("Encrypted PDF opened with an empty password (permissions-only)")
    return reader
