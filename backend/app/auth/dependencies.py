"""FastAPI dependencies for cookie-based authentication and CSRF
protection. Shared by every route (in any domain) that needs to know the
current authenticated user, or must guard against IDOR by verifying
resource ownership.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.errors import AuthUnauthorizedError
from app.auth.models import User
from app.auth.services import AuthService
from app.core.config import settings
from app.database.session import get_db


def _raw_token_from_request(request: Request) -> str | None:
    return request.cookies.get(settings.AUTH_COOKIE_NAME)


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """Returns the authenticated user if the request carries a valid
    session cookie, else None. Never raises — routes that work for both
    anonymous and authenticated callers (e.g. session creation) use this."""
    service = AuthService(db)
    resolved = service.get_current_user(_raw_token_from_request(request))
    return resolved[0] if resolved else None


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Returns the authenticated user or raises AuthUnauthorizedError (401,
    generic message) — for routes that require login."""
    service = AuthService(db)
    resolved = service.get_current_user(_raw_token_from_request(request))
    if not resolved:
        raise AuthUnauthorizedError("Authentication required.")
    return resolved[0]


def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check for cookie-authenticated mutating
    endpoints: the CSRF cookie value (unreadable cross-site by a third
    party page since it requires JS running on our own origin to read and
    echo it back) must match the header the client sends. Only meaningful
    once a session cookie exists; a request with no auth cookie has
    nothing to protect."""
    if not request.cookies.get(settings.AUTH_COOKIE_NAME):
        return
    cookie_value = request.cookies.get(settings.AUTH_CSRF_COOKIE_NAME)
    header_value = request.headers.get(settings.AUTH_CSRF_HEADER_NAME)
    if not cookie_value or not header_value or cookie_value != header_value:
        raise AuthUnauthorizedError("Missing or invalid CSRF token.")
