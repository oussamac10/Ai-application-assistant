from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.forms.public_schemas import PublicFormDetail
from app.forms.public_service import PublicFormService

router = APIRouter(tags=["public-forms"])


def _extract_frontend_origin(request: Request) -> str:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        p = urlparse(referer)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    return "http://localhost:3000"


@router.get("/public/forms/{identifier}/qr")
def get_public_form_qr(
    identifier: str,
    request: Request,
    format: str = Query("png", pattern="^(png|svg)$"),
    db: Session = Depends(get_db),
) -> Response:
    frontend_origin = _extract_frontend_origin(request)
    service = PublicFormService(db)
    qr_bytes, mime = service.get_qr_bytes(
        identifier, fmt=format, frontend_origin=frontend_origin
    )
    return Response(
        content=qr_bytes,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/public/forms/{identifier}/counter-poster.pdf")
def get_public_form_counter_poster(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    frontend_origin = _extract_frontend_origin(request)
    service = PublicFormService(db)
    pdf_bytes, filename = service.get_counter_poster_bytes(
        identifier, frontend_origin=frontend_origin
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/public/forms/{identifier}", response_model=PublicFormDetail)
def get_public_form(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicFormDetail:
    frontend_origin = _extract_frontend_origin(request)
    service = PublicFormService(db)
    return service.get_public_form_detail(identifier, frontend_origin=frontend_origin)


@router.get("/public/forms/{org_slug}/{form_key}/qr")
def get_org_public_form_qr(
    org_slug: str,
    form_key: str,
    request: Request,
    format: str = Query("png", pattern="^(png|svg)$"),
    db: Session = Depends(get_db),
) -> Response:
    return get_public_form_qr(f"{org_slug}/{form_key}", request, format, db)


@router.get("/public/forms/{org_slug}/{form_key}/counter-poster.pdf")
def get_org_public_form_counter_poster(
    org_slug: str,
    form_key: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    return get_public_form_counter_poster(f"{org_slug}/{form_key}", request, db)


@router.get("/public/forms/{org_slug}/{form_key}", response_model=PublicFormDetail)
def get_org_public_form(
    org_slug: str,
    form_key: str,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicFormDetail:
    return get_public_form(f"{org_slug}/{form_key}", request, db)
