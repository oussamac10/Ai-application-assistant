from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.auth.schemas import LoginRequest, RegisterRequest, UserResponse
from app.auth.security import generate_csrf_token
from app.auth.services import AuthService
from app.core.config import settings
from app.database.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, raw_token: str) -> None:
    csrf_token = generate_csrf_token()
    max_age = settings.AUTH_SESSION_TTL_HOURS * 3600
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )
    # Readable by our own frontend JS (not HttpOnly) so it can be echoed
    # back as the X-CSRF-Token header — that is the double-submit check,
    # not secrecy of this value.
    response.set_cookie(
        key=settings.AUTH_CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(settings.AUTH_CSRF_COOKIE_NAME, path="/")


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    service = AuthService(db)
    user = service.register(body.email, body.password, body.password_confirmation)
    _, raw_token = service.login(body.email, body.password)
    _set_auth_cookies(response, raw_token)
    return user


@router.post("/login", response_model=UserResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    service = AuthService(db)
    user, raw_token = service.login(body.email, body.password)
    _set_auth_cookies(response, raw_token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = AuthService(db)
    raw_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    service.logout(raw_token)
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(require_user)) -> User:
    return user


@router.post("/refresh", response_model=UserResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> User:
    service = AuthService(db)
    raw_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    new_user, new_raw_token = service.refresh(raw_token)
    _set_auth_cookies(response, new_raw_token)
    return new_user
