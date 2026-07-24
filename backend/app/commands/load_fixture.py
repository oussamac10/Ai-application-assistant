import logging
import sys

from app.database.session import SessionLocal
from app.forms.models import FormTemplate
from app.forms.schemas import (
    FieldCreate,
    OptionSchema,
    OptionTranslationSchema,
    TranslationSchema,
)
from app.forms.services import FormService

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_basic_registration_fixture() -> None:
    db = SessionLocal()
    service = FormService(db)

    try:
        # Check if the fixture template already exists, and clean it up first
        logger.info("Checking for existing 'basic-registration' template...")
        existing_template = (
            db.query(FormTemplate).filter_by(key="basic-registration").first()
        )
        if existing_template:
            logger.info("Cleaning up existing 'basic-registration' template...")
            # FormVersion cascade deletes fields, translations,
            # options, and option translations
            for v in existing_template.versions:
                db.delete(v)
            db.delete(existing_template)
            db.commit()
            logger.info("Cleaned up successfully.")

        # 1. Create Template
        logger.info("Creating FormTemplate 'basic-registration'...")
        template = service.create_template(
            key="basic-registration",
            name="Basic Registration",
            description="A multilingual registration form with basic fields.",
        )

        # 2. Create Draft Version (Languages: en, de, ar)
        logger.info("Creating draft version 1...")
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en", "de", "ar"],
        )

        # 3. Add fields
        fields_to_add = [
            FieldCreate(
                key="first_name",
                field_type="person_name",
                required=True,
                position=1,
                configuration={"maxLength": 100, "requiresConfirmation": True},
                translations=[
                    TranslationSchema(
                        language="en",
                        label="First Name",
                        placeholder="Enter your first name",
                    ),
                    TranslationSchema(
                        language="de",
                        label="Vorname",
                        placeholder="Geben Sie Ihren Vornamen ein",
                    ),
                    TranslationSchema(
                        language="ar",
                        label="الاسم الأول",
                        placeholder="أدخل اسمك الأول",
                    ),
                ],
            ),
            FieldCreate(
                key="last_name",
                field_type="person_name",
                required=True,
                position=2,
                configuration={"maxLength": 100, "requiresConfirmation": True},
                translations=[
                    TranslationSchema(
                        language="en",
                        label="Last Name",
                        placeholder="Enter your last name",
                    ),
                    TranslationSchema(
                        language="de",
                        label="Nachname",
                        placeholder="Geben Sie Ihren Nachnamen ein",
                    ),
                    TranslationSchema(
                        language="ar",
                        label="الاسم الأخير",
                        placeholder="أدخل اسمك الأخير",
                    ),
                ],
            ),
            FieldCreate(
                key="date_of_birth",
                field_type="date",
                required=True,
                position=3,
                configuration={"requiresConfirmation": True},
                translations=[
                    TranslationSchema(
                        language="en", label="Date of Birth", placeholder="YYYY-MM-DD"
                    ),
                    TranslationSchema(
                        language="de", label="Geburtsdatum", placeholder="JJJJ-MM-TT"
                    ),
                    TranslationSchema(
                        language="ar", label="تاريخ الميلاد", placeholder="YYYY-MM-DD"
                    ),
                ],
            ),
            FieldCreate(
                key="email",
                field_type="email",
                required=True,
                position=4,
                configuration={"requiresConfirmation": True},
                translations=[
                    TranslationSchema(
                        language="en",
                        label="Email Address",
                        placeholder="Enter your email address",
                    ),
                    TranslationSchema(
                        language="de",
                        label="E-Mail-Adresse",
                        placeholder="Geben Sie Ihre E-Mail-Adresse ein",
                    ),
                    TranslationSchema(
                        language="ar",
                        label="البريد الإلكتروني",
                        placeholder="أدخل بريدك الإلكتروني",
                    ),
                ],
            ),
            FieldCreate(
                key="country",
                field_type="country",
                required=True,
                position=5,
                configuration={"requiresConfirmation": True},
                translations=[
                    TranslationSchema(
                        language="en",
                        label="Country",
                        placeholder="Select your country",
                    ),
                    TranslationSchema(
                        language="de", label="Land", placeholder="Wählen Sie Ihr Land"
                    ),
                    TranslationSchema(
                        language="ar", label="البلد", placeholder="اختر بلدك"
                    ),
                ],
            ),
            FieldCreate(
                key="marital_status",
                field_type="single_choice",
                required=True,
                position=6,
                configuration={"requiresConfirmation": True},
                translations=[
                    TranslationSchema(
                        language="en",
                        label="Marital Status",
                        placeholder="Select your marital status",
                    ),
                    TranslationSchema(
                        language="de",
                        label="Familienstand",
                        placeholder="Wählen Sie Ihren Familienstand",
                    ),
                    TranslationSchema(
                        language="ar",
                        label="الحالة الاجتماعية",
                        placeholder="اختر حالتك الاجتماعية",
                    ),
                ],
                options=[
                    OptionSchema(
                        value="single",
                        position=1,
                        translations=[
                            OptionTranslationSchema(language="en", label="Single"),
                            OptionTranslationSchema(language="de", label="Ledig"),
                            OptionTranslationSchema(language="ar", label="عازب"),
                        ],
                    ),
                    OptionSchema(
                        value="married",
                        position=2,
                        translations=[
                            OptionTranslationSchema(language="en", label="Married"),
                            OptionTranslationSchema(language="de", label="Verheiratet"),
                            OptionTranslationSchema(language="ar", label="متزوج"),
                        ],
                    ),
                    OptionSchema(
                        value="divorced",
                        position=3,
                        translations=[
                            OptionTranslationSchema(language="en", label="Divorced"),
                            OptionTranslationSchema(language="de", label="Geschieden"),
                            OptionTranslationSchema(language="ar", label="مطلق"),
                        ],
                    ),
                    OptionSchema(
                        value="widowed",
                        position=4,
                        translations=[
                            OptionTranslationSchema(language="en", label="Widowed"),
                            OptionTranslationSchema(language="de", label="Verwitwet"),
                            OptionTranslationSchema(language="ar", label="أرمل"),
                        ],
                    ),
                ],
            ),
        ]

        for fc in fields_to_add:
            logger.info(f"Adding field '{fc.key}' to version {version.id}...")
            service.add_field_to_draft(version.id, fc)

        # 4. Publish Version
        logger.info(f"Publishing version {version.id}...")
        service.publish_version(version.id)
        logger.info("Fixture 'Basic Registration' loaded and published successfully!")

    except Exception:
        logger.exception("Failed to load development fixture")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    load_basic_registration_fixture()
