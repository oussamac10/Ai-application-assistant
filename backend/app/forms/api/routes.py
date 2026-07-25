from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.session import get_db
from app.forms.models import FormField, FormTemplate, FormVersion
from app.forms.schemas import (
    FieldCreate,
    FieldResponse,
    FieldUpdate,
    PublishedFormResponse,
    TemplateCreate,
    TemplateResponse,
    VersionCreate,
    VersionResponse,
)
from app.forms.services import FormService

router = APIRouter()


# Templates
@router.post(
    "/forms",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    data: TemplateCreate, db: Session = Depends(get_db)
) -> FormTemplate:
    service = FormService(db)
    return service.create_template(
        key=data.key, name=data.name, description=data.description
    )


@router.get("/forms", response_model=list[TemplateResponse])
def list_templates(db: Session = Depends(get_db)) -> list[FormTemplate]:
    service = FormService(db)
    return service.list_templates()


@router.get("/forms/{form_id}", response_model=TemplateResponse)
def get_template(form_id: str, db: Session = Depends(get_db)) -> FormTemplate:
    service = FormService(db)
    return service.get_template(form_id)


# Versions
@router.post(
    "/forms/{form_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_draft_version(
    form_id: str, data: VersionCreate, db: Session = Depends(get_db)
) -> FormVersion:
    service = FormService(db)
    return service.create_draft_version(
        form_template_id=form_id,
        source_language=data.source_language,
        supported_output_languages=data.supported_output_languages,
    )


@router.get("/form-versions/{version_id}", response_model=VersionResponse)
def get_version(version_id: str, db: Session = Depends(get_db)) -> FormVersion:
    service = FormService(db)
    return service.get_version(version_id)


# Fields
@router.post(
    "/form-versions/{version_id}/fields",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_field_to_draft(
    version_id: str, data: FieldCreate, db: Session = Depends(get_db)
) -> FormField:
    service = FormService(db)
    return service.add_field_to_draft(version_id, data)


@router.patch("/form-fields/{field_id}", response_model=FieldResponse)
def update_draft_field(
    field_id: str, data: FieldUpdate, db: Session = Depends(get_db)
) -> FormField:
    service = FormService(db)
    return service.update_draft_field(field_id, data)


# Publish & Clone
@router.post("/form-versions/{version_id}/publish", response_model=VersionResponse)
def publish_version(version_id: str, db: Session = Depends(get_db)) -> FormVersion:
    service = FormService(db)
    return service.publish_version(version_id)


@router.post(
    "/form-versions/{version_id}/clone",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def clone_version(version_id: str, db: Session = Depends(get_db)) -> FormVersion:
    service = FormService(db)
    return service.clone_version(version_id)


@router.get("/published-forms", response_model=list[PublishedFormResponse])
def list_published_forms(db: Session = Depends(get_db)) -> Any:
    stmt = (
        select(FormVersion)
        .options(joinedload(FormVersion.template))
        .where(FormVersion.status == "published")
        .order_by(FormVersion.published_at.desc())
    )
    versions = db.scalars(stmt).unique().all()

    result = []
    for v in versions:
        result.append(
            {
                "id": v.id,
                "template_key": v.template.key,
                "name": v.template.name,
                "description": v.template.description,
                "version_number": v.version_number,
                "source_language": v.source_language,
                "supported_output_languages": v.supported_output_languages,
            }
        )
    return result
