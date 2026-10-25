"""Fernet envelope encryption for transient session tokens returned via job polling.

Ensures raw anonymous session tokens are NEVER stored in plaintext in Postgres
or Redis while allowing a legitimate document owner polling `GET /api/jobs/{id}`
to receive the session credential created asynchronously by a worker.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _build_fernet() -> Fernet:
    secret = (
        settings.SESSION_TOKEN_SECRET
        or settings.AUTH_SECRET
        or "local-dev-ephemeral-job-token-key"
    )
    derived = hashlib.sha256(f"job-token-v1:{secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_job_token(raw_token: str | None) -> str | None:
    if not raw_token:
        return None
    return _build_fernet().encrypt(raw_token.encode("utf-8")).decode("ascii")


def decrypt_job_token(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    try:
        return _build_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None
