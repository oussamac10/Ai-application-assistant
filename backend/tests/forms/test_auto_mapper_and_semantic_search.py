"""Tests for Phase G5-AI: Semantic Intelligence, Vector Search & Auto-Mapping."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.embedding.mock import MockEmbeddingProvider
from app.ai.embedding.similarity import cosine_similarity, rank_by_similarity
from app.auth.models import User
from app.database.session import SessionLocal
from app.forms.auto_mapper import SchemaAutoMapperService
from app.forms.models import FormField, FormTemplate, FormVersion
from app.forms.semantic_search import MultilingualSemanticSearchService
from app.main import app  # registers declarative ORM mappers
from app.organizations.models import Organization, OrganizationMember


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.asyncio
async def test_mock_embedding_provider_and_similarity():
    provider = MockEmbeddingProvider()
    assert provider.dimensions == 128

    vec1 = await provider.get_embedding("Vorname des Kindes")
    vec2 = await provider.get_embedding("First name of applicant")
    vec3 = await provider.get_embedding("Bankverbindung IBAN Kontonummer")

    # Normalized vectors have unit L2 norm
    norm_sq = sum(x * x for x in vec1)
    assert abs(norm_sq - 1.0) < 1e-4

    # Semantically close concepts (both first name) should have high cosine similarity
    sim_names = cosine_similarity(vec1, vec2)
    assert sim_names > 0.65

    # Completely different concept (name vs bank IBAN) should have lower similarity
    sim_unrelated = cosine_similarity(vec1, vec3)
    assert sim_names > sim_unrelated

    # Rank by similarity test
    candidates = [vec2, vec3]
    ranked = rank_by_similarity(vec1, candidates)
    assert ranked[0][0] == 0  # vec2 ranked first


@pytest.mark.asyncio
async def test_schema_auto_mapper_service(db_session: Session):
    uid = uuid.uuid4().hex[:8]
    # Setup test user and organization
    user = User(
        email=f"officer-{uid}@municipality.de",
        password_hash="testpass",
        status="active",
        normalized_email=f"officer-{uid}@municipality.de",
    )
    db_session.add(user)
    db_session.flush()

    org = Organization(
        name="Stadt Köln",
        slug=f"stadt-koeln-{uid}",
        organization_type="government",
    )
    db_session.add(org)
    db_session.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="editor",
    )
    db_session.add(member)

    template = FormTemplate(
        organization_id=org.id,
        key=f"anmeldung-koeln-{uid}",
        name="Wohnsitz Anmeldung",
        description="Offizielle Anmeldung einer Wohnung in Köln",
    )
    db_session.add(template)
    db_session.flush()

    version = FormVersion(
        form_template_id=template.id,
        version_number=1,
        status="draft",
        source_language="de",
        supported_output_languages=["de"],
    )
    db_session.add(version)
    db_session.flush()

    # Add detected fields without pre-fill question_key
    f1 = FormField(
        form_version_id=version.id,
        key="vorname_antragsteller",
        field_type="string",
        required=True,
        position=1,
        configuration={"label": "Vorname der antragstellenden Person"},
    )
    f2 = FormField(
        form_version_id=version.id,
        key="nachname_antragsteller",
        field_type="string",
        required=True,
        position=2,
        configuration={"label": "Familienname / Nachname"},
    )
    f3 = FormField(
        form_version_id=version.id,
        key="geburtsdatum",
        field_type="date",
        required=True,
        position=3,
        configuration={"label": "Tag der Geburt (Geburtsdatum)"},
    )
    f4 = FormField(
        form_version_id=version.id,
        key="bank_iban",
        field_type="string",
        required=False,
        position=4,
        configuration={"label": "IBAN Bankverbindung"},
    )
    f5 = FormField(
        form_version_id=version.id,
        key="unterschrift",
        field_type="signature",
        required=True,
        position=5,
        configuration={"label": "Eigenhändige Unterschrift"},
    )

    db_session.add_all([f1, f2, f3, f4, f5])
    db_session.commit()

    # Run Auto-Mapper
    mapper = SchemaAutoMapperService(db_session, MockEmbeddingProvider())
    results = await mapper.auto_map_fields(org.id, template.id)

    assert len(results) == 5

    res_by_key = {r.field_key: r for r in results}

    # Verify high-confidence mappings
    assert (
        res_by_key["vorname_antragsteller"].suggested_question_key
        == "personal.first_name"
    )
    assert res_by_key["vorname_antragsteller"].confidence >= 0.80

    assert (
        res_by_key["nachname_antragsteller"].suggested_question_key
        == "personal.last_name"
    )
    assert res_by_key["nachname_antragsteller"].confidence >= 0.80

    assert res_by_key["geburtsdatum"].suggested_question_key == "person.date_of_birth"
    assert res_by_key["geburtsdatum"].confidence >= 0.80

    assert res_by_key["bank_iban"].suggested_question_key == "financial.iban"
    assert res_by_key["bank_iban"].confidence >= 0.80

    assert res_by_key["unterschrift"].suggested_question_key == "signature.applicant"
    assert res_by_key["unterschrift"].confidence >= 0.80

    # Apply Mappings
    mappings_to_apply = [
        {"field_id": r.field_id, "question_key": r.suggested_question_key}
        for r in results
        if r.suggested_question_key
    ]
    applied_count = mapper.apply_auto_mappings(org.id, template.id, mappings_to_apply)
    assert applied_count == 5

    # Verify persistence
    db_session.refresh(f1)
    db_session.refresh(f5)
    assert f1.question_key == "personal.first_name"
    assert f5.question_key == "signature.applicant"


@pytest.mark.asyncio
async def test_multilingual_semantic_form_search(db_session: Session):
    uid = uuid.uuid4().hex[:8]
    org_slug = f"muenchen-portal-{uid}"
    org = Organization(
        name="Bürgeramt München",
        slug=org_slug,
        organization_type="government",
    )
    db_session.add(org)
    db_session.flush()

    # Template 1: Residence Registration
    t1 = FormTemplate(
        organization_id=org.id,
        key=f"anmeldung-wohnung-{uid}",
        name="Anmeldung einer Wohnung",
        description="Amtliche Wohnsitzanmeldung bei Umzug innerhalb oder nach München",
        instructions="Bitte bringen Sie die Wohnungsgeberbestätigung Ihres Vermieters mit.",
    )
    db_session.add(t1)
    db_session.flush()

    v1 = FormVersion(
        form_template_id=t1.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de"],
    )
    db_session.add(v1)

    # Template 2: Dog Tax Registration (unrelated)
    t2 = FormTemplate(
        organization_id=org.id,
        key=f"hundesteuer-{uid}",
        name="Hundesteuer Anmeldung",
        description="Anmeldung eines Hundes zur Besteuerung",
        instructions="Geben Sie Rasse und Geburtsdatum des Hundes an.",
    )
    db_session.add(t2)
    db_session.flush()

    v2 = FormVersion(
        form_template_id=t2.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de"],
    )
    db_session.add(v2)
    db_session.commit()

    searcher = MultilingualSemanticSearchService(db_session, MockEmbeddingProvider())

    # Search with German query
    results_de = await searcher.search_organization_forms(org_slug, "Wohnung anmelden")
    assert len(results_de) >= 1
    assert results_de[0].template_id == t1.id

    # Search with English query
    results_en = await searcher.search_organization_forms(
        org_slug, "register new residence apartment"
    )
    assert len(results_en) >= 1
    assert results_en[0].template_id == t1.id


def test_public_semantic_search_api_route(db_session: Session):
    uid = uuid.uuid4().hex[:8]
    org_slug = f"frankfurt-search-{uid}"
    org = Organization(
        name="Stadt Frankfurt",
        slug=org_slug,
        organization_type="government",
    )
    db_session.add(org)
    db_session.flush()

    template = FormTemplate(
        organization_id=org.id,
        key=f"anmeldung-frankfurt-{uid}",
        name="Anmeldung einer Wohnung",
        description="Wohnsitz anmelden in Frankfurt am Main",
        instructions="Bringen Sie Ihren Personalausweis mit.",
    )
    db_session.add(template)
    db_session.flush()

    version = FormVersion(
        form_template_id=template.id,
        version_number=1,
        status="published",
        source_language="de",
        supported_output_languages=["de"],
    )
    db_session.add(version)
    db_session.commit()

    client = TestClient(app)
    res = client.get(
        f"/api/public/organizations/{org_slug}/forms/semantic-search?q=Wohnung"
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["key"] == f"anmeldung-frankfurt-{uid}"
    assert "relevance_score" in data[0]
