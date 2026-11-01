from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.auth.schemas import (
    AccountDataExportResponse,
    ActionStatusResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenConfirmRequest,
    UserResponse,
)
from app.auth.security import generate_csrf_token
from app.auth.services import AuthService
from app.core.config import settings
from app.core.rate_limit import rate_limit_auth
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
    _rate_limit: None = Depends(rate_limit_auth),
) -> UserResponse:
    service = AuthService(db)
    user = service.register(body.email, body.password, body.password_confirmation)
    _, raw_token = service.login(body.email, body.password)
    _set_auth_cookies(response, raw_token)

    resp = UserResponse.model_validate(user)
    if body.account_type in ("government", "business"):
        from app.organizations.services import OrganizationService

        org_service = OrganizationService(db)
        org, member = org_service.create_organization_for_user(
            user=user,
            name=body.organization_name or "",
            organization_type=body.account_type,
            official_website_url=body.official_website_url,
        )
        resp.account_type = org.organization_type
        resp.organization_id = org.id
        resp.organization_role = member.role
    else:
        resp.account_type = "individual"

    return resp


@router.post("/login", response_model=UserResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
) -> UserResponse:
    service = AuthService(db)
    user, raw_token = service.login(body.email, body.password)
    _set_auth_cookies(response, raw_token)

    from app.organizations.repositories import OrganizationRepository

    org_repo = OrganizationRepository(db)
    membership = org_repo.get_user_membership(user.id)
    org = org_repo.get(membership.organization_id) if membership else None

    resp = UserResponse.model_validate(user)
    if org and membership:
        resp.account_type = getattr(org, "organization_type", "government")
        resp.organization_id = org.id
        resp.organization_role = membership.role
    else:
        resp.account_type = "individual"

    return resp


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
def me(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> UserResponse:
    from app.organizations.repositories import OrganizationRepository

    org_repo = OrganizationRepository(db)
    membership = org_repo.get_user_membership(user.id)
    org = org_repo.get(membership.organization_id) if membership else None

    resp = UserResponse.model_validate(user)
    if org and membership:
        resp.account_type = getattr(org, "organization_type", "government")
        resp.organization_id = org.id
        resp.organization_role = membership.role
    else:
        resp.account_type = "individual"

    return resp


@router.get("/me/export", response_model=AccountDataExportResponse)
def export_me(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    response.headers["Cache-Control"] = "no-store"
    service = AuthService(db)
    return service.export_account_data(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = AuthService(db)
    service.delete_account(user)
    _clear_auth_cookies(response)


@router.post(
    "/verify-email/request",
    response_model=ActionStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_email_verification(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
    _rate_limit: None = Depends(rate_limit_auth),
) -> Any:
    service = AuthService(db)
    service.request_email_verification(user)
    return {"status": "sent"}


@router.post("/verify-email/confirm", response_model=UserResponse)
def confirm_email_verification(
    body: TokenConfirmRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
) -> User:
    service = AuthService(db)
    return service.confirm_email_verification(body.token)


@router.post(
    "/password-reset/request",
    response_model=ActionStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
) -> Any:
    service = AuthService(db)
    service.request_password_reset(body.email)
    return {"status": "accepted"}


@router.post("/password-reset/confirm", response_model=ActionStatusResponse)
def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    response: Response,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
) -> Any:
    service = AuthService(db)
    service.confirm_password_reset(
        body.token, body.password, body.password_confirmation
    )
    _clear_auth_cookies(response)
    return {"status": "password_reset"}


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
