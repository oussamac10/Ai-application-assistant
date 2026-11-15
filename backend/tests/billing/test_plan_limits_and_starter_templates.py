from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.main  # noqa: F401 - register all SQLAlchemy models
from app.auth.models import User
from app.billing.services import B2B_PLANS, get_published_template_limit
from app.database.session import SessionLocal
from app.forms.models import FormTemplate, FormVersion
from app.forms.starter_templates import (
    STARTER_TEMPLATE_KEYS,
    provision_starter_templates_for_organization,
)
from app.organizations.services import OrganizationService


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


def test_published_template_limits_match_b2b_plans() -> None:
    assert (
        get_published_template_limit("agency_sandbox")
        == B2B_PLANS["agency_sandbox"]["max_published_templates"]
        == 5
    )
    assert (
        get_published_template_limit("agency_pro")
        == B2B_PLANS["agency_pro"]["max_published_templates"]
        == 25
    )
    assert (
        get_published_template_limit("enterprise")
        == B2B_PLANS["enterprise"]["max_published_templates"]
        == 200
    )
    # Legacy aliases and unknown keys resolve safely to canonical tiers
    assert get_published_template_limit("free") == 5
    assert get_published_template_limit("pro") == 25
    assert get_published_template_limit("unknown_plan") == 5


def test_new_organization_auto_provisions_three_starter_templates(
    db_session: Session,
) -> None:
    user = User(
        email="trial@relocation-demo.de",
        normalized_email="trial@relocation-demo.de",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    org, _ = OrganizationService(db_session).ensure_default_organization(user)

    # New org starts empty by default; explicit provisioning adds 3 starter templates
    initial_templates = (
        db_session.query(FormTemplate)
        .filter(FormTemplate.organization_id == org.id)
        .all()
    )
    assert initial_templates == []

    provisioned = provision_starter_templates_for_organization(db_session, org)
    assert len(provisioned) == len(STARTER_TEMPLATE_KEYS)

    templates = (
        db_session.query(FormTemplate)
        .filter(FormTemplate.organization_id == org.id)
        .all()
    )
    assert len(templates) == len(STARTER_TEMPLATE_KEYS)

    for tpl in templates:
        published_versions = (
            db_session.query(FormVersion)
            .filter(
                FormVersion.form_template_id == tpl.id,
                FormVersion.status == "published",
            )
            .all()
        )
        assert len(published_versions) == 1

    # Re-running provisioning is strictly idempotent
    second_pass = provision_starter_templates_for_organization(db_session, org)
    assert second_pass == []
