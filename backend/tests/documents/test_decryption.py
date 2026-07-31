"""Encrypted is not the same as locked.

The reported failure: `32-41-1268-antrag-aufenthaltserlaubnis.pdf`
(Landeshauptstadt Stuttgart) was rejected with "PDF is encrypted or
password-protected." It opens in every PDF viewer without a prompt — it is
encrypted for *permissions* (no printing, no editing) with an empty user
password, which is how essentially every government form is published.

The old check asked `reader.is_encrypted`, which answers "does this file have
an encryption dictionary?" and says nothing about whether it can be read. The
only way to answer that is to try opening it.
"""

from __future__ import annotations

from pathlib import Path

import pypdf
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.documents.decryption import (
    PDF_DECRYPTION_FAILED,
    PDF_INVALID,
    PDF_PASSWORD_REQUIRED,
    open_pdf,
)
from app.documents.errors import DocumentValidationError


def _plain_pdf(path: Path, pages: int = 3) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    for index in range(pages):
        c.drawString(72, 720, f"Nachname: ____________  (page {index + 1})")
        c.showPage()
    c.save()
    return path


def _encrypt(
    source: Path, target: Path, *, user: str, owner: str | None = None
) -> Path:
    reader = pypdf.PdfReader(str(source))
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=user, owner_password=owner)
    with open(target, "wb") as handle:
        writer.write(handle)
    return target


def test_an_unencrypted_pdf_opens(tmp_path: Path) -> None:
    reader = open_pdf(_plain_pdf(tmp_path / "plain.pdf"))

    assert len(reader.pages) == 3


def test_a_permissions_encrypted_pdf_opens_with_an_empty_password(
    tmp_path: Path,
) -> None:
    """The reported failure, reproduced and fixed."""
    source = _plain_pdf(tmp_path / "plain.pdf")
    encrypted = _encrypt(source, tmp_path / "perm.pdf", user="", owner="owner-secret")

    # It really is encrypted — otherwise this test proves nothing.
    assert pypdf.PdfReader(str(encrypted)).is_encrypted is True

    reader = open_pdf(encrypted)

    assert len(reader.pages) == 3


def test_every_page_survives_decryption(tmp_path: Path) -> None:
    """A readable encrypted document must not be silently truncated — the
    Stuttgart form is three pages and all three must reach detection."""
    source = _plain_pdf(tmp_path / "plain.pdf", pages=3)
    encrypted = _encrypt(source, tmp_path / "perm.pdf", user="", owner="owner")

    reader = open_pdf(encrypted)

    assert len(reader.pages) == 3
    for page in reader.pages:
        # Content is reachable, not just counted. pypdf reports a successful
        # decrypt and then fails on first access when the AES provider is
        # missing, which is a deployment problem, not a document one.
        assert page.extract_text() is not None


def test_a_genuinely_locked_pdf_reports_password_required(tmp_path: Path) -> None:
    source = _plain_pdf(tmp_path / "plain.pdf")
    locked = _encrypt(source, tmp_path / "locked.pdf", user="s3cret")

    with pytest.raises(DocumentValidationError) as exc:
        open_pdf(locked)

    assert exc.value.error_code == PDF_PASSWORD_REQUIRED


def test_a_file_that_is_not_a_pdf_reports_invalid(tmp_path: Path) -> None:
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf at all")

    with pytest.raises(DocumentValidationError) as exc:
        open_pdf(broken)

    assert exc.value.error_code == PDF_INVALID


def test_a_corrupted_encrypted_pdf_reports_decryption_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dependency gap or a damaged encryption dictionary is not the user's
    password, and must not be reported as one."""
    source = _plain_pdf(tmp_path / "plain.pdf")
    encrypted = _encrypt(source, tmp_path / "perm.pdf", user="", owner="owner")

    def _explode(self: object, password: str) -> int:
        raise RuntimeError("cryptography is required for AES")

    monkeypatch.setattr(pypdf.PdfReader, "decrypt", _explode)

    with pytest.raises(DocumentValidationError) as exc:
        open_pdf(encrypted)

    assert exc.value.error_code == PDF_DECRYPTION_FAILED


def test_no_error_ever_carries_document_content_or_a_password(
    tmp_path: Path,
) -> None:
    """pypdf messages can echo object contents, and document contents are
    private. The password the user tried is never repeated back either."""
    source = _plain_pdf(tmp_path / "plain.pdf")
    locked = _encrypt(source, tmp_path / "locked.pdf", user="hunter2-secret")

    with pytest.raises(DocumentValidationError) as exc:
        open_pdf(locked)

    message = str(exc.value)
    assert "hunter2-secret" not in message
    assert "Nachname" not in message
