from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.commands.seed_german_templates import (
    GERMAN_TEMPLATE_SPECS,
    generate_german_pdf_fixtures,
    seed_german_templates,
)
from app.database.session import SessionLocal
from app.documents.analyzer import PDFAnalyzer
from app.documents.registry import PDFFingerprintRegistry
from app.main import app
from app.questions.repositories import QuestionRepository
from app.questions.seed import seed_catalog
from app.sessions.models import FormSession
from app.sessions.services import SessionService


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_seed_catalog_supports_all_eight_ui_languages(db_session: Session) -> None:
    seed_catalog(db_session)
    repo = QuestionRepository(db_session)

    required_locales = {"en", "de", "fr", "ar", "tr", "uk", "es", "ru"}
    expected_keys = [
        "personal.first_name",
        "personal.last_name",
        "personal.date_of_birth",
        "contact.email",
        "contact.phone",
        "address.street",
        "address.postal_code",
        "address.city",
        "address.country",
        "finance.iban",
        "residence.move_in_date",
        "residence.landlord_name",
    ]

    for qkey in expected_keys:
        definition = repo.get_definition(qkey)
        assert definition is not None, f"Missing question definition: {qkey}"
        for locale in required_locales:
            trans = repo.get_translation(definition.id, locale)
            assert trans is not None, f"Missing translation for {qkey} [{locale}]"
            assert trans.review_status == "approved"
            assert len(trans.text.strip()) > 3


def test_top_ten_german_templates_seed_idempotently_and_match_fingerprints(
    db_session: Session,
    client: TestClient,
    tmp_path: Path,
) -> None:
    assert len(GERMAN_TEMPLATE_SPECS) >= 10

    generate_german_pdf_fixtures(output_dir=tmp_path)
    seeded_versions = seed_german_templates(db_session, fixtures_dir=tmp_path)
    assert len(seeded_versions) == len(GERMAN_TEMPLATE_SPECS)

    # Verify every generated PDF matches its exact fingerprint unambiguously
    analyzer = PDFAnalyzer()
    registry = PDFFingerprintRegistry(fixtures_dir=tmp_path)
    for spec in GERMAN_TEMPLATE_SPECS:
        pdf_key = f"{spec['key']}-v1"
        pdf_path = tmp_path / f"{pdf_key}.pdf"
        mapping_path = tmp_path / f"{pdf_key}.mapping.json"
        fp_path = tmp_path / f"{pdf_key}.fingerprint.json"

        assert pdf_path.exists()
        assert mapping_path.exists()
        assert fp_path.exists()

        analysis = analyzer.analyze_document(str(pdf_path))
        matched = registry.match_document(str(pdf_path), analysis)
        assert matched is not None, f"Fingerprint failed to match {pdf_key}"
        assert matched["templateKey"] == pdf_key
        assert matched["formKey"] == spec["key"]

    # Create a live session against the first seeded template, then re-run seed_german_templates
    # to prove idempotency preserves existing sessions and versions.
    session_service = SessionService(db_session)
    created_session, _ = session_service.create_session(
        form_version_id=seeded_versions[0].id,
        user_language="tr",
        output_language="de",
    )

    reseeded_versions = seed_german_templates(db_session, fixtures_dir=tmp_path)
    assert [v.id for v in reseeded_versions] == [v.id for v in seeded_versions]

    still_exists = db_session.get(FormSession, created_session.id)
    assert still_exists is not None

    # Verify GET /api/published-forms exposes all 10 German predefined templates
    resp = client.get("/api/published-forms")
    assert resp.status_code == 200
    returned_keys = {item["templateKey"] for item in resp.json()}
    for spec in GERMAN_TEMPLATE_SPECS:
        assert spec["key"] in returned_keys
