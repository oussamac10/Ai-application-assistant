"""Application-layer Fernet envelope encryption for `user_profile_entries`.

Derives a dedicated 256-bit key (`VAULT_ENCRYPTION_KEY` when explicitly configured,
or domain-separated `SHA-256("profile-vault-v1:" + AUTH_SECRET)`) so personal profile
values are never persisted in plaintext in PostgreSQL.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _build_vault_fernet() -> Fernet:
    explicit = (settings.VAULT_ENCRYPTION_KEY or "").strip()
    base_secret = (
        explicit
        or settings.AUTH_SECRET
        or settings.SESSION_TOKEN_SECRET
        or "local-dev-ephemeral-profile-vault-key"
    )
    derived = hashlib.sha256(f"profile-vault-v1:{base_secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_vault_payload(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return _build_vault_fernet().encrypt(serialized.encode("utf-8")).decode("ascii")


def decrypt_vault_payload(ciphertext: str) -> dict[str, Any]:
    try:
        raw = _build_vault_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except (InvalidToken, ValueError, TypeError):
        return {}
