"""Publishes the signature demo form, for development and test only.

The committed signature template and its mapping were reachable only from
tests, so the one flow they exist to prove — fill a field, sign or defer, export
a PDF with the signature in the right place — could not be walked in a browser.

    docker compose exec backend python -m app.commands.load_signature_demo

Refuses to run when `ENVIRONMENT` is production. A demo form appearing in a
public list is not a cosmetic problem: someone would fill it in and export a
document that means nothing.

Idempotent. Re-running replaces the previous version rather than adding a
second, so repeated fixture commands cannot leave two identical forms in the
list.
"""

from __future__ import annotations

import logging
import sys

from app.answers.models import FormAnswer
from app.core.config import settings
from app.database.session import SessionLocal
from app.forms.models import FormTemplate
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.sessions.models import FormSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPLATE_KEY = "signature-demo"
PDF_TEMPLATE_KEY = "signature-demo-v1"


def load_signature_demo_fixture() -> None:
    if settings.is_production:
        logger.error(
            "Refusing to publish the signature demo form: ENVIRONMENT=%s. "
            "It is a development fixture and must never appear in a public "
            "form list.",
            settings.ENVIRONMENT,
        )
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(FormTemplate).filter_by(key=TEMPLATE_KEY).first()
        if existing:
            logger.info("Replacing the existing signature demo form...")
            # Answers and sessions reference fields and versions, so they go
            # first or the foreign keys refuse the delete.
            for version in existing.versions:
                for field in version.fields:
                    db.query(FormAnswer).filter_by(field_id=field.id).delete(
                        synchronize_session=False
                    )
                db.query(FormSession).filter_by(form_version_id=version.id).delete(
                    synchronize_session=False
                )
                db.delete(version)
            db.delete(existing)
            db.commit()

        service = FormService(db)
        template = service.create_template(
            key=TEMPLATE_KEY,
            name="Signature demo (development)",
            description=(
                "Development fixture for the signature capture and export flow."
            ),
        )
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en", "de", "fr", "ar"],
        )
        # Binds the form to the committed PDF and its mapping, which is what
        # gives the export a signature rectangle to draw into.
        version.pdf_template_key = PDF_TEMPLATE_KEY
        db.commit()

        service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="applicant_name",
                field_type="person_name",
                requiredness="required",
                position=1,
                translations=[
                    TranslationSchema(language="en", label="Full name"),
                    TranslationSchema(language="de", label="Vollständiger Name"),
                    TranslationSchema(language="fr", label="Nom complet"),
                    TranslationSchema(language="ar", label="الاسم الكامل"),
                ],
            ),
        )
        service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="applicant_signature",
                field_type="signature",
                # Required, deliberately: it is the case worth demonstrating.
                # A required signature still allows signing on paper — the
                # document must be signed before it counts, not signed here.
                requiredness="required",
                position=2,
                translations=[
                    TranslationSchema(language="en", label="Applicant signature"),
                    TranslationSchema(language="de", label="Unterschrift"),
                    TranslationSchema(language="fr", label="Signature du demandeur"),
                    TranslationSchema(language="ar", label="توقيع مقدم الطلب"),
                ],
            ),
        )
        service.publish_version(version.id)

        logger.info(
            "Signature demo form published (template=%s, pdf=%s).",
            TEMPLATE_KEY,
            PDF_TEMPLATE_KEY,
        )
    except Exception:
        logger.exception("Failed to load the signature demo fixture")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    load_signature_demo_fixture()
