"""Password hashing and auth-session-token security.

Password hashing uses Argon2id (via argon2-cffi) — never a reversible or
fast general-purpose hash. Auth session tokens follow the exact same
HMAC-SHA256-hash-at-rest, one-time-raw-exposure pattern already used for
anonymous ownership tokens (see app/sessions/security.py): the raw token is
returned to the client exactly once and only its hash is ever stored.
"""

import hashlib
import hmac
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_password_hasher = PasswordHasher()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    """Deterministic case-insensitive normalization used for uniqueness
    and lookups. Does not alter the original `email` value shown back to
    the user."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Any other verification error (e.g. an unrecognized/corrupt hash)
        # must fail closed, never raise past the caller as a 500 that could
        # leak information about the stored hash format.
        return False


def needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


def generate_auth_token() -> str:
    """Generate a cryptographically secure random auth session token."""
    return secrets.token_urlsafe(32)


def hash_auth_token(token: str) -> str:
    secret = settings.AUTH_SECRET
    if not secret:
        raise ValueError("AUTH_SECRET is not configured.")
    return hmac.new(
        secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_auth_token(token: str, token_hash: str) -> bool:
    computed_hash = hash_auth_token(token)
    return hmac.compare_digest(computed_hash, token_hash)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
