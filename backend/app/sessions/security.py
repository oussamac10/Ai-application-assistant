import hashlib
import hmac
import secrets

from app.core.config import settings


def generate_ownership_token() -> str:
    """Generate a cryptographically secure random session ownership token."""
    return secrets.token_urlsafe(32)


def hash_ownership_token(token: str) -> str:
    """Hash the ownership token using HMAC-SHA256 with the server-side secret."""
    secret = settings.SESSION_TOKEN_SECRET
    if not secret:
        raise ValueError("SESSION_TOKEN_SECRET is not configured.")
    return hmac.new(
        secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_ownership_token(token: str, token_hash: str) -> bool:
    """Safely verify the ownership token against the stored hash in constant time."""
    computed_hash = hash_ownership_token(token)
    return hmac.compare_digest(computed_hash, token_hash)
